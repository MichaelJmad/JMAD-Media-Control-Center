# JMCC Website & Release Portal Setup Guide

This folder contains the official showcase website and update server configuration for **JMAD Media Control Center (JMCC)**.

To maintain the application as **closed-source** while distributing release packages and showcasing the app publically, follow this step-by-step infrastructure guide.

---

## Part 1: GitHub Repository Architecture

To keep your source code private while sharing the app, use a two-repository setup:

1. **`JMCC-source` (Private Repo):** Holds the actual application source code (everything in `K:\Projects\JMCC` *except* this `website` directory).
2. **`JMCC` (Public Repo):** Holds *only* the contents of this `website/` directory. This hosts the documentation, landing page, and auto-update configuration via GitHub Pages.

---

## Part 2: Setting up the Public Repository

### 1. Create the Repo
Go to GitHub and create a new repository:
- **Repository name:** `JMCC` (or your preferred public name)
- **Visibility:** **Public**
- **Initialize this repository with:** Do NOT add a README, `.gitignore`, or License (keep it blank).

### 2. Push the Website Directory to GitHub
Open PowerShell, navigate to this `website/` directory, and run the following commands to initialize and push:

```powershell
# Navigate to the website directory
cd K:\Projects\JMCC\website

# Initialize a new independent git repository
git init -b main

# Stage all files (html, css, js, mockups, version.json)
git add .

# Commit files
git commit -m "Initial commit of JMCC website and update API"

# Link to your new public GitHub repository
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/JMCC.git

# Force-push to set upstream main branch
git push -u origin main --force
```

### 3. Enable GitHub Pages
1. Go to your repository on GitHub.
2. Click on **Settings** (gear icon) in the top tabs.
3. In the left sidebar under "Code and automation", click on **Pages**.
4. Under "Build and deployment", set the source to **Deploy from a branch**.
5. Set the branch to **`main`** and folder to **`/ (root)`**.
6. Click **Save**.
7. GitHub will deploy the site in 1-2 minutes. Your website URL will be:  
   `https://YOUR_GITHUB_USERNAME.github.io/JMCC/`

---

## Part 3: Deploying a Release Package (v2.4.2-rc.1)

### 1. Build the Distribution Assets
Run the local script in the root of your project:
```powershell
.\package.ps1
```
This compiles the application and generates the output packages inside `dist-app/`:
- `JMAD Media Control Center 2.4.2-rc.1.exe` (Portable executable)
- `JMAD Media Control Center-2.4.2-rc.1-win.zip` (Portable ZIP archive)
- `JMAD Media Control Center Setup 2.4.2-rc.1.exe` (NSIS Installer executable)

### 2. Create a GitHub Release
1. On your public `JMCC` repository page on GitHub, click on **Releases** (on the right-side panel) -> **Create a new release**.
2. Set the **Choose a tag** field to `v2.4.2-rc.1` (click "Create new tag on publish").
3. Set the release title to `v2.4.2-rc.1 Beta`.
4. Write your release notes (changelog).
5. Drag and drop the generated files from `dist-app/` into the upload box:
   - `JMAD Media Control Center-2.4.2-rc.1-win.zip`
   - `JMAD Media Control Center Setup 2.4.2-rc.1.exe`
6. Click **Publish release**.

---

## Part 4: Auto-Update Integration

The desktop app performs update checking against the version schema stored in the public repo:  
`https://YOUR_GITHUB_USERNAME.github.io/JMCC/api/update/version.json`

### When releasing a new version:
1. Obtain the final file size (in bytes) and calculate the **SHA-256 hash** of the Setup Installer:
   ```powershell
   Get-FileHash -Algorithm SHA256 "dist-app\JMAD Media Control Center Setup 2.4.2-rc.1.exe"
   ```
2. Edit `api/update/version.json` in your local website folder:
   - Update `"version"` to the new tag.
   - Insert the download link of the new release assets.
   - Insert the calculated SHA-256 checksum in the `"sha256"` field.
   - Set the size in bytes under `"sizeBytes"`.
3. Commit and push the changes:
   ```powershell
   git add api/update/version.json
   git commit -m "Release v2.4.2-rc.1 update metadata"
   git push origin main
   ```
   *Within minutes, all running instances of JMAD Media Control Center will detect the update and prompt the user to download!*
