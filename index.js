// ─── TAB NAVIGATION SYSTEM ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Navigation tabs handler
  const navButtons = document.querySelectorAll('.nav-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTabId = btn.getAttribute('data-tab');
      
      // Deactivate all buttons and tabs
      navButtons.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(pane => pane.classList.remove('active'));

      // Activate selected
      btn.classList.add('active');
      const targetPane = document.getElementById(targetTabId);
      if (targetPane) {
        targetPane.classList.add('active');
      }

      // Scroll to top
      window.scrollTo(0, 0);
    });
  });

  // Getting started sidebar menu handler
  const menuItems = document.querySelectorAll('.menu-item');
  const stepPanes = document.querySelectorAll('.step-pane');

  menuItems.forEach(item => {
    item.addEventListener('click', () => {
      const stepId = item.getAttribute('data-step');

      // Deactivate all steps
      menuItems.forEach(i => i.classList.remove('active'));
      stepPanes.forEach(pane => pane.classList.remove('active'));

      // Activate selected
      item.classList.add('active');
      const targetStepPane = document.getElementById(stepId);
      if (targetStepPane) {
        targetStepPane.classList.add('active');
      }
    });
  });

  // Fetch dynamic version details from update endpoint
  fetchVersionDetails();
});

// Switch tabs programmatically (e.g. from CTA click)
function switchTab(tabId) {
  const targetBtn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
  if (targetBtn) {
    targetBtn.click();
  }
}

// ─── COPY TO CLIPBOARD HELPER ──────────────────────────────────
function copyText(text, element) {
  navigator.clipboard.writeText(text).then(() => {
    // Save original inner HTML
    const originalHTML = element.innerHTML;
    
    // Provide visual feedback
    if (element.classList.contains('crypto-chip')) {
      element.innerHTML = `SHA-256: Copied! <i class="fa-solid fa-check" style="color: var(--color-accent);"></i>`;
    } else {
      element.innerHTML = `<i class="fa-solid fa-check" style="color: var(--color-accent);"></i>`;
    }

    // Reset after delay
    setTimeout(() => {
      element.innerHTML = originalHTML;
    }, 2000);
  }).catch(err => {
    console.error('Failed to copy text: ', err);
  });
}

// ─── DYNAMIC VERSION & BUILD INFO FETCH ────────────────────────
async function fetchVersionDetails() {
  const downloadSizeEl = document.getElementById('download-size');
  const shaHashEl = document.getElementById('sha256-setup-hash');

  try {
    const response = await fetch('./api/update/version.json');
    if (!response.ok) throw new Error('Network error loading version details');
    
    const data = await response.json();
    
    // Update setup installer specs
    const winExe = data.downloads?.windows?.exe;
    const sizeBytes = data.downloads?.windows?.sizeBytes;
    const sha256 = data.downloads?.windows?.sha256;

    if (sizeBytes && sizeBytes > 0) {
      const mbSize = (sizeBytes / (1024 * 1024)).toFixed(1);
      downloadSizeEl.innerText = `${mbSize} MB`;
    } else {
      downloadSizeEl.innerText = 'Pending Build';
    }

    if (sha256) {
      shaHashEl.innerText = sha256;
    } else {
      shaHashEl.innerText = 'Pending Build Generation';
    }
  } catch (error) {
    console.warn('Could not load version.json, using fallback build values.', error);
    downloadSizeEl.innerText = 'N/A';
    shaHashEl.innerText = 'Awaiting final checksum generation';
  }
}
