"""
Interactive Double-Slit Experiment  ·  Premium Redesign
=========================================================
Key improvements over v1:
  • 2D Huygens-Fresnel wave field (animated, showing actual wave propagation)
  • Physical barrier with slits drawn dynamically on the 2D panel
  • Proper analytical intensity via complex wave superposition + sinc envelope
  • Live fringe spacing annotation (λL/d) on the wave field
  • Pause / Resume animation toggle
  • Detection screen accumulates particle hits probabilistically

Controls:
  Slit Separation  — sets distance between the two slit centres
  Slit Width       — controls diffraction envelope (wider slit → narrower pattern)
  Wavelength  λ    — longer λ → wider fringe spacing
  1 Slit / 2 Slits — toggles interference on/off for visual comparison
  Fire Particles   — samples 300 photon hits from the intensity distribution
  Reset Hits       — clears all particle detections
  Pause / Resume   — freezes or unfreezes the animated wave
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.widgets as widgets
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle

# ─── Theme ────────────────────────────────────────────────────────────────────
plt.style.use('dark_background')
matplotlib.rcParams.update({
    'font.family'    : 'DejaVu Sans',
    'axes.titlesize' : 10,
    'axes.labelsize' : 8,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 8,
})

# ─── Colours ──────────────────────────────────────────────────────────────────
BG    = '#04040f'
PANEL = '#08082a'

# 2D wave field: dark navy → blue → white → orange → dark red
wave_cmap = LinearSegmentedColormap.from_list('wave', [
    '#04040f', '#06064a', '#1133cc', '#5599ff',
    '#ddeeff', '#ffcc44', '#ff5500', '#990000', '#04040f'
], N=512)

# Screen heatmap: dark → violet → red → gold → white
screen_cmap = LinearSegmentedColormap.from_list('sc', [
    '#04040f', '#0d003d', '#4400aa', '#aa44ff',
    '#ff4488', '#ff7700', '#ffee00', '#ffffff'
], N=256)

C_SEP  = '#7C4DFF'   # slider – slit separation
C_W    = '#00BCD4'   # slider – slit width
C_LAM  = '#69F0AE'   # slider – wavelength
C_INT  = '#FF5252'   # 2-slit intensity curve
C_REF  = '#40C4FF'   # 1-slit reference curve
C_HIT  = '#00E5FF'   # particle hit dots  (bright cyan – contrasts warm screen heatmap)
C_SLIT = '#00E5FF'   # slit opening glow
C_SARR = '#FFD740'   # slit width arrow / label

# ─── Initial parameters ───────────────────────────────────────────────────────
INIT_SEP  = 3.0
INIT_W    = 1.0
INIT_LAM  = 2.5
INIT_N    = 2

# ─── Grids ────────────────────────────────────────────────────────────────────
# 2D propagation field  (rows=y, cols=x)
NY_F, NX_F  = 180, 280
y_field     = np.linspace(-8,  8,  NY_F)
x_field     = np.linspace(0.3, 18, NX_F)
X_F, Y_F    = np.meshgrid(x_field, y_field)

# Screen
SCREEN_X = 15.0
y_scr    = np.linspace(-7, 7, 700)

# ─── Physics ──────────────────────────────────────────────────────────────────
def huygens_field(sep, lam, n_slits, phase=0.0):
    """
    2D Huygens-Fresnel snapshot.
    Each slit emits a cylindrical wave:  cos(k·r - phase) / sqrt(r)
    Interference fringes emerge from path-length differences.
    """
    k   = 2 * np.pi / lam
    r1  = np.sqrt(X_F**2 + (Y_F - sep / 2) ** 2)
    psi = np.cos(k * r1 - phase) / np.sqrt(np.maximum(r1, 0.4))
    if n_slits == 2:
        r2   = np.sqrt(X_F**2 + (Y_F + sep / 2) ** 2)
        psi += np.cos(k * r2 - phase) / np.sqrt(np.maximum(r2, 0.4))
    return psi


def screen_intensity(sep, width, lam, n_slits):
    """
    Analytical far-field intensity at the screen.
    Uses complex Huygens amplitude with a sinc² diffraction envelope
    from the finite slit width:
        I(y) ∝ |Σ_j  sinc(π·w·sinθ/λ) · exp(i·k·r_j) / √r_j |²
    """
    k        = 2 * np.pi / lam
    theta    = np.arctan2(y_scr, SCREEN_X)
    # np.sinc(x) = sin(πx)/(πx)  →  sinc(w·sinθ/λ) = sin(π·w·sinθ/λ)/(π·w·sinθ/λ)
    envelope = np.sinc(width * np.sin(theta) / lam)

    r1   = np.sqrt(SCREEN_X**2 + (y_scr - sep / 2) ** 2)
    psi  = envelope * np.exp(1j * k * r1) / np.sqrt(r1)
    if n_slits == 2:
        r2   = np.sqrt(SCREEN_X**2 + (y_scr + sep / 2) ** 2)
        psi += envelope * np.exp(1j * k * r2) / np.sqrt(r2)

    I = np.abs(psi) ** 2
    return I / I.max()


def fringe_dy(sep, lam):
    """Theoretical fringe spacing on screen: Δy = λ·L / d"""
    return lam * SCREEN_X / sep

# ─── State ────────────────────────────────────────────────────────────────────
phase_val     = [0.0]
animating     = [True]
particle_hits = []

# ─── Initial data ─────────────────────────────────────────────────────────────
field_0 = huygens_field(INIT_SEP, INIT_LAM, INIT_N)
I_0     = screen_intensity(INIT_SEP, INIT_W, INIT_LAM, INIT_N)
I_ref_0 = screen_intensity(INIT_SEP, INIT_W, INIT_LAM, 1)

# ─── Figure ───────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
fig.patch.set_facecolor(BG)

gs = GridSpec(
    2, 2, figure=fig,
    left=0.05, right=0.98, top=0.93, bottom=0.29,
    hspace=0.55, wspace=0.18,
    width_ratios=[2.8, 1.0],
    height_ratios=[2.2, 1.0],
)

ax_2d     = fig.add_subplot(gs[0, 0])
ax_screen = fig.add_subplot(gs[0, 1])
ax_1d     = fig.add_subplot(gs[1, :])

for ax in (ax_2d, ax_screen, ax_1d):
    ax.set_facecolor(PANEL)
    for sp in ax.spines.values():
        sp.set_color('#20204a')
    ax.tick_params(colors='#556688')

fig.suptitle('⚛  Double-Slit Experiment  ·  Interactive Physics Demo',
             fontsize=14, fontweight='bold', color='#ccd4ff', y=0.975)

# ══════════════════════════════════════════════════════════════════════════════
# PANEL 1 – 2D Huygens-Fresnel Wave Propagation
# ══════════════════════════════════════════════════════════════════════════════
vmax_0 = np.abs(field_0).max() * 0.65
im_2d = ax_2d.imshow(
    field_0, aspect='auto', origin='lower',
    extent=[x_field[0], x_field[-1], y_field[0], y_field[-1]],
    cmap=wave_cmap, vmin=-vmax_0, vmax=vmax_0,
    interpolation='bilinear',
)

# Screen position marker
ax_2d.axvline(SCREEN_X, color='#6688cc', lw=1.8, ls='--', alpha=0.85, zorder=4)

# Slit point-source markers (updated dynamically)
slit_dots = ax_2d.scatter(
    [x_field[0] + 0.15, x_field[0] + 0.15], [INIT_SEP / 2, -INIT_SEP / 2],
    s=90, c='white', zorder=10, edgecolors='#aabbdd', linewidths=1.2,
)

# Barrier rectangles + slit annotations (all managed by draw_barrier())
barrier_patches = []
slit_annots     = []   # arrows + text labels showing slit width

def draw_barrier(sep, width, n_slits):
    """
    Redraw the opaque barrier with slit openings for current parameters.
    Slit openings are highlighted with a cyan glow and annotated with a
    double-headed arrow + label showing the current slit width value.
    """
    for p in barrier_patches:
        p.remove()
    barrier_patches.clear()
    for a in slit_annots:
        a.remove()
    slit_annots.clear()

    bx   = x_field[0] - 0.30
    bw   = 0.55
    bx_r = bx + bw                         # right edge of barrier
    kw   = dict(color='#b8ccff', alpha=0.90, zorder=7, lw=0)
    glow = dict(color=C_SLIT,   alpha=0.28, zorder=8, lw=0)  # slit glow
    hs   = sep / 2
    hw   = max(width / 2, 0.10)
    ymax = y_field[-1]
    ymin = y_field[0]

    def add_wall(y0, y1):
        h = y1 - y0
        if h > 0.02:
            barrier_patches.append(
                ax_2d.add_patch(Rectangle((bx, y0), bw, h, **kw))
            )

    def add_slit_glow(y_lo, y_hi):
        """Cyan-tinted overlay on the open slit gap."""
        h = y_hi - y_lo
        if h > 0.01:
            barrier_patches.append(
                ax_2d.add_patch(Rectangle((bx, y_lo), bw, h, **glow))
            )

    def add_width_arrow(y_centre):
        """
        Double-headed arrow + 'w=X.XX' label just to the right of the barrier,
        spanning from (y_centre - hw) to (y_centre + hw).
        """
        x_arrow = bx_r + 0.18
        # Arrow drawn as annotate from bottom to top of slit
        arr = ax_2d.annotate(
            '', xy=(x_arrow, y_centre + hw), xytext=(x_arrow, y_centre - hw),
            arrowprops=dict(
                arrowstyle='<->', color=C_SARR, lw=1.4, mutation_scale=9,
            ),
            zorder=10,
        )
        lbl = ax_2d.text(
            x_arrow + 0.22, y_centre, f'w={width:.2f}',
            fontsize=6.5, color=C_SARR, va='center', ha='left', zorder=10,
            path_effects=[pe.withStroke(linewidth=2.5, foreground=BG)],
        )
        slit_annots.extend([arr, lbl])

    if n_slits == 2:
        add_wall(hs + hw, ymax)        # above upper slit
        add_wall(-(hs - hw), hs - hw)  # between the two slits
        add_wall(ymin, -(hs + hw))     # below lower slit
        add_slit_glow(hs - hw, hs + hw)       # upper slit glow
        add_slit_glow(-(hs + hw), -(hs - hw)) # lower slit glow
        add_width_arrow( hs)   # label for upper slit
        add_width_arrow(-hs)   # label for lower slit
    else:                              # single slit centred at y=0
        add_wall(hw, ymax)
        add_wall(ymin, -hw)
        add_slit_glow(-hw, hw)
        add_width_arrow(0.0)

draw_barrier(INIT_SEP, INIT_W, INIT_N)

# Fringe-spacing annotation line pair and text
dy0 = fringe_dy(INIT_SEP, INIT_LAM)
fringe_lines = [
    ax_2d.axhline(  dy0 / 2, xmin=0.82, xmax=0.95,
                    color=C_HIT, lw=1.4, ls='-', alpha=0.85, zorder=6),
    ax_2d.axhline(- dy0 / 2, xmin=0.82, xmax=0.95,
                    color=C_HIT, lw=1.4, ls='-', alpha=0.85, zorder=6),
    ax_2d.axhline(0,          xmin=0.82, xmax=0.95,
                    color=C_HIT, lw=0.7, ls=':', alpha=0.50, zorder=6),
]
fringe_lbl = ax_2d.text(
    x_field[-1] - 0.3, dy0 / 2 + 0.3, f'Δy = {dy0:.2f}',
    fontsize=7.5, color=C_HIT, ha='right', va='bottom',
    path_effects=[pe.withStroke(linewidth=2.5, foreground=PANEL)],
)

# Static labels
for txt, xpos, col in [
    ('Slit plane', x_field[0] + 0.6,  '#aaccff'),
    ('Screen',     SCREEN_X + 0.25,   '#6688cc'),
]:
    ax_2d.text(xpos, y_field[-1] * 0.88, txt,
               fontsize=7.5, color=col, ha='left',
               path_effects=[pe.withStroke(linewidth=2, foreground=PANEL)])

# Colourbar
cb = fig.colorbar(im_2d, ax=ax_2d, fraction=0.022, pad=0.015)
cb.set_label('Wave Amplitude', color='#8899bb', fontsize=7)
cb.ax.tick_params(colors='#667799', labelsize=6)

ax_2d.set_xlabel('Propagation Distance  (a.u.)', labelpad=3)
ax_2d.set_ylabel('Transverse Position  (a.u.)', labelpad=3)
ax_2d.set_title('2D Wave Propagation  ·  Huygens–Fresnel  (live animated)',
                color='#ccd4ff')

# ══════════════════════════════════════════════════════════════════════════════
# PANEL 2 – Detection Screen
# ══════════════════════════════════════════════════════════════════════════════
im_screen = ax_screen.imshow(
    I_0[:, np.newaxis], aspect='auto', origin='lower',
    extent=[0, 1, y_scr[0], y_scr[-1]],
    cmap=screen_cmap, vmin=0, vmax=1,
    interpolation='bilinear',
)

# Intensity profile line overlay on the screen
line_scr, = ax_screen.plot(
    I_0 * 0.88, y_scr, color='#ffffff', lw=1.4, alpha=0.85, zorder=5,
)

# Cyan dots with thin white edges so they pop against every part of the heatmap
scat_hits = ax_screen.scatter(
    [], [], s=9, c=C_HIT, alpha=0.90, lw=0.4,
    edgecolors='white', zorder=6,
)

ax_screen.set_xlim(0, 1)
ax_screen.set_ylim(y_scr[0], y_scr[-1])
ax_screen.set_xticks([])
ax_screen.set_title('Detection Screen', color='#ccd4ff')
ax_screen.set_ylabel('Position  (a.u.)')
ax_screen.set_xlabel('← Intensity', labelpad=2)

hit_lbl = ax_screen.text(
    0.97, 0.98, '0 hits', transform=ax_screen.transAxes,
    ha='right', va='top', color=C_HIT, fontsize=8, fontweight='bold',
    path_effects=[pe.withStroke(linewidth=2.5, foreground='#000010')],
)

# ══════════════════════════════════════════════════════════════════════════════
# PANEL 3 – 1D Intensity Profile
# ══════════════════════════════════════════════════════════════════════════════
fill_ref  = [ax_1d.fill_between(y_scr, I_ref_0, color=C_REF, alpha=0.15)]
fill_main = [ax_1d.fill_between(y_scr, I_0,     color=C_INT, alpha=0.30)]
line_ref, = ax_1d.plot(y_scr, I_ref_0, color=C_REF, lw=1.2, ls='--',
                        alpha=0.75, label='1-Slit  (no interference)')
line_1d,  = ax_1d.plot(y_scr, I_0,     color=C_INT, lw=2.0,
                        label='2-Slit  intensity')

ax_1d.set_xlim(y_scr[0], y_scr[-1])
ax_1d.set_ylim(0, 1.35)
ax_1d.axhline(0, color='#20204a', lw=0.7)
ax_1d.set_xlabel('Position on Screen  (a.u.)')
ax_1d.set_ylabel('Intensity  (a.u.)')
ax_1d.set_title('1D Intensity Profile at Screen', color='#ccd4ff')
ax_1d.legend(loc='upper right',
             facecolor='#0d0d35', edgecolor='#3a3a6a', labelcolor='white')

# ══════════════════════════════════════════════════════════════════════════════
# WIDGETS
# ══════════════════════════════════════════════════════════════════════════════
def _sl_ax(bot):
    a = fig.add_axes([0.10, bot, 0.46, 0.023])
    a.set_facecolor('#08082a')
    for sp in a.spines.values():
        sp.set_color('#20204a')
    return a

sl_sep = widgets.Slider(_sl_ax(0.232), 'Slit Separation', 1.0, 8.0,
                         valinit=INIT_SEP, color=C_SEP, initcolor='none')
sl_w   = widgets.Slider(_sl_ax(0.191), 'Slit Width',       0.2, 3.0,
                         valinit=INIT_W,   color=C_W,   initcolor='none')
sl_lam = widgets.Slider(_sl_ax(0.150), 'Wavelength  λ',    0.5, 6.0,
                         valinit=INIT_LAM, color=C_LAM, initcolor='none')

for sl in (sl_sep, sl_w, sl_lam):
    sl.label.set_color('#ccd4ff')
    sl.valtext.set_color('#8899bb')

ax_radio    = fig.add_axes([0.63, 0.120, 0.13, 0.125], facecolor='#08082a')
ax_btn_fire = fig.add_axes([0.78, 0.205, 0.100, 0.043])
ax_btn_rst  = fig.add_axes([0.78, 0.152, 0.100, 0.043])
ax_btn_anim = fig.add_axes([0.78, 0.099, 0.100, 0.043])

for ax in (ax_radio, ax_btn_fire, ax_btn_rst, ax_btn_anim):
    for sp in ax.spines.values():
        sp.set_color('#20204a')

radio = widgets.RadioButtons(
    ax_radio, ('1 Slit', '2 Slits'), active=1,
    label_props={'color': ['#ccd4ff', '#ccd4ff']},
    radio_props={'facecolor': [C_REF, C_INT], 'edgecolor': ['#fff', '#fff']},
)

btn_fire = widgets.Button(ax_btn_fire, '⚡ Fire Particles',
                          color='#0c0c40', hovercolor='#2a1a70')
btn_rst  = widgets.Button(ax_btn_rst,  '✕ Reset Hits',
                          color='#0c0c40', hovercolor='#4a1a1a')
btn_anim = widgets.Button(ax_btn_anim, '|| Pause Wave',
                          color='#0c0c40', hovercolor='#1a3a1a')

for btn, col in [(btn_fire, C_HIT), (btn_rst, '#FF8A80'), (btn_anim, '#69F0AE')]:
    btn.label.set_color(col)
    btn.label.set_fontsize(8)

# Physics readout line
phys_txt = fig.text(0.10, 0.118, '', fontsize=7.5, color='#8899bb',
                     va='top', family='monospace')

def _update_annotations(sep, width, lam, n):
    """Refresh fringe-spacing lines and physics text."""
    if n == 2:
        dy = fringe_dy(sep, lam)
        dy_clamped = min(dy, 5.5)
        fringe_lines[0].set_ydata([ dy_clamped / 2,  dy_clamped / 2])
        fringe_lines[1].set_ydata([-dy_clamped / 2, -dy_clamped / 2])
        fringe_lines[2].set_ydata([0, 0])
        fringe_lbl.set_position((x_field[-1] - 0.3, dy_clamped / 2 + 0.25))
        fringe_lbl.set_text(f'Δy = {dy:.2f}')
        for fl in fringe_lines:
            fl.set_visible(True)
        fringe_lbl.set_visible(True)
        phys_txt.set_text(
            f'd = {sep:.2f}  │  w = {width:.2f}  │  λ = {lam:.2f}  │  '
            f'Fringe spacing  Δy = λL/d = {dy:.2f}'
        )
    else:
        for fl in fringe_lines:
            fl.set_visible(False)
        fringe_lbl.set_visible(False)
        phys_txt.set_text(
            f'w = {width:.2f}  │  λ = {lam:.2f}  │  '
            f'Single-slit diffraction only — no interference fringes'
        )

_update_annotations(INIT_SEP, INIT_W, INIT_LAM, INIT_N)

# ─── Callbacks ────────────────────────────────────────────────────────────────
def update(_=None):
    sep   = sl_sep.val
    width = sl_w.val
    lam   = sl_lam.val
    n     = 1 if radio.value_selected == '1 Slit' else 2

    # Barrier + slit markers
    draw_barrier(sep, width, n)
    if n == 2:
        slit_dots.set_offsets([[x_field[0] + 0.15,  sep / 2],
                                [x_field[0] + 0.15, -sep / 2]])
        slit_dots.set_sizes([90, 90])
    else:
        slit_dots.set_offsets([[x_field[0] + 0.15, 0.0]])
        slit_dots.set_sizes([90])

    # Screen intensity
    I     = screen_intensity(sep, width, lam, n)
    I_ref = screen_intensity(sep, width, lam, 1)

    im_screen.set_data(I[:, np.newaxis])
    line_scr.set_xdata(I * 0.88)

    # 1D profile
    line_1d.set_ydata(I)
    line_ref.set_ydata(I_ref)
    line_1d.set_label(f'{"2-Slit" if n == 2 else "1-Slit"}  intensity')
    fill_main[0].remove()
    fill_ref[0].remove()
    fill_main[0] = ax_1d.fill_between(y_scr, I,     color=C_INT, alpha=0.30)
    fill_ref[0]  = ax_1d.fill_between(y_scr, I_ref, color=C_REF, alpha=0.15)
    ax_1d.set_ylim(0, max(I.max(), I_ref.max()) * 1.35)
    ax_1d.legend(loc='upper right',
                 facecolor='#0d0d35', edgecolor='#3a3a6a', labelcolor='white')

    # Annotations
    _update_annotations(sep, width, lam, n)

    # If animation is paused, also refresh the wave field snapshot
    if not animating[0]:
        psi  = huygens_field(sep, lam, n, phase_val[0])
        vmax = np.abs(psi).max() * 0.65
        im_2d.set_data(psi)
        im_2d.set_clim(-vmax, vmax)

    fig.canvas.draw_idle()


def fire_particles(_):
    sep   = sl_sep.val
    width = sl_w.val
    lam   = sl_lam.val
    n     = 1 if radio.value_selected == '1 Slit' else 2
    I     = screen_intensity(sep, width, lam, n)
    prob  = I / I.sum()
    idxs  = np.random.choice(len(y_scr), size=300, p=prob)
    hits  = y_scr[idxs] + np.random.normal(0, 0.04, len(idxs))
    particle_hits.extend(hits.tolist())
    ys = np.array(particle_hits)
    xs = np.random.uniform(0.05, 0.88, len(ys))
    scat_hits.set_offsets(np.column_stack([xs, ys]))
    hit_lbl.set_text(f'{len(particle_hits)} hits')
    fig.canvas.draw_idle()


def reset_hits(_):
    particle_hits.clear()
    scat_hits.set_offsets(np.empty((0, 2)))
    hit_lbl.set_text('0 hits')
    fig.canvas.draw_idle()


def toggle_anim(_):
    animating[0] = not animating[0]
    btn_anim.label.set_text(
        '|| Pause Wave' if animating[0] else '> Resume Wave'
    )
    fig.canvas.draw_idle()


sl_sep.on_changed(update)
sl_w.on_changed(update)
sl_lam.on_changed(update)
radio.on_clicked(update)
btn_fire.on_clicked(fire_particles)
btn_rst.on_clicked(reset_hits)
btn_anim.on_clicked(toggle_anim)

# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION – wave phase scrolling
# ══════════════════════════════════════════════════════════════════════════════
def anim_frame(frame):
    """Advance wave phase so it appears to flow outward from the slits."""
    if not animating[0]:
        return (im_2d,)
    sep = sl_sep.val
    lam = sl_lam.val
    n   = 1 if radio.value_selected == '1 Slit' else 2
    phase_val[0] = frame * 0.20
    psi  = huygens_field(sep, lam, n, phase_val[0])
    vmax = np.abs(psi).max() * 0.65
    im_2d.set_data(psi)
    im_2d.set_clim(-vmax, vmax)
    return (im_2d,)


anim_obj = animation.FuncAnimation(
    fig, anim_frame, frames=500, interval=45, blit=True,
)

# ─── Footer ───────────────────────────────────────────────────────────────────
fig.text(
    0.10, 0.082,
    'Fringe spacing  Δy = λL/d    │    '
    'Envelope  ~ sinc²(π·w·sinθ/λ)    │    '
    'Interference fringes vanish with 1 slit',
    color='#33334488', fontsize=7.5,
)

# Save a static preview and open the interactive window
plt.savefig('double_slit.png', dpi=150, facecolor=fig.get_facecolor())
print('Saved: double_slit.png')
plt.show()
