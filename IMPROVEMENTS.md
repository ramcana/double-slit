# Demo improvement roadmap

## Highest impact

1. **Guided experiment mode** — lead learners through predictions, one-slit
   diffraction, two-slit interference, and a short interpretation quiz.
2. **Real units and presets** — add nanometres, micrometres, metres, and presets
   for electrons, red/green/blue light, and a representative lab geometry.
3. **True single-photon pacing** — fire one, ten, or many detections; add a speed
   control and time-lapse so the interference distribution visibly emerges.
4. **Coherence and phase controls** — demonstrate fringe visibility by changing
   relative phase, temporal coherence, slit illumination balance, and which-path
   information.
5. **Model validation** — regression-test symmetry, normalization, one-slit
   minima, fringe spacing, and limiting cases against analytical results.

## Presentation and teaching

- Add labelled near-field/Fresnel and far-field/Fraunhofer modes.
- Overlay predicted maxima and minima, with a toggle to hide the answer.
- Provide tooltips defining wavelength, slit width, separation, and intensity.
- Include an accessible light theme, keyboard controls, reduced-motion mode,
  colour-blind-safe palettes, and screen-reader-friendly live values.
- Add shareable URLs that encode the current parameter values.
- Export a screenshot, hit data CSV, or short animation for lab reports.
- Add translations and a teacher worksheet with learning objectives.

## Physics depth

- Numerically integrate across finite slit apertures instead of applying only a
  far-field sinc envelope.
- Add partial coherence and finite spectral bandwidth.
- Compare classical waves with quantum probability amplitudes while explaining
  that the observed intensity distribution is mathematically shared.
- Add detector resolution, background noise, exposure time, and Poisson counts.
- Add a which-path detector and show loss/recovery of visibility.
- Offer electron de Broglie wavelength presets without implying photons and
  massive particles share identical apparatus physics.

## Engineering and project polish

- Split calculation, state, and rendering code into testable modules.
- Add type hints, docstrings, formatting/linting, and CI on supported Python
  versions.
- Package a command-line entry point and add headless image generation.
- Add browser unit tests and a visual smoke test for the Pages demo.
- Publish tagged releases with screenshots and a changelog.
- Add a short demo GIF, repository topics, social preview image, and citation
  metadata (`CITATION.cff`) once authorship details are known.

