# Design & Architecture Notes

This document tracks design decisions and suggestions made during development that deviate from or add to the original development plan.

---

## Settings Dialog UI Redesign

- **Date:** October 18, 2025
- **Change:** The Settings Dialog UI has been redesigned from the originally planned top-level tabbed layout.
- **New Design:** It now uses a more modern and scalable sidebar layout, implemented with a `QListWidget` for categories on the left and a `QStackedWidget` for the corresponding pages on the right.
- **Reason:** This was suggested by the user for better scalability and user experience as more settings categories are added.
- **Action:** The main development plan should be updated to reflect this new, superior layout.
