# Seth Reee Arch packages

Signed x86_64 and ARM64 (`aarch64`) packages for Archivist, Tether, Vigilant, Portalview, and Scry. Once configured, installed apps update through **Omarchy Update** / `omarchy update` alongside normal system packages.

## Installation

On an Omarchy device, download and review the installer, then run it:

```bash
curl -fL https://seth-reee.github.io/omarchy-packages/install.sh -o /tmp/seth-reee-repo-install.sh
less /tmp/seth-reee-repo-install.sh
sudo bash /tmp/seth-reee-repo-install.sh
omarchy update
```

The installer verifies the signing-key fingerprint, imports and locally trusts that key, and adds a dedicated repository configuration. It backs up existing configuration before changing it. Package and repository database signatures are required.

Signing key fingerprint:

```text
186C035DEE6A26BD035AB1D3319FE7C0F23D8AE5
```

After the update, install any apps you do not already have:

```bash
sudo pacman -S --needed archivist tether vigilant portalview scry
```

You can choose individual names. This configuration works unchanged on x86_64 and ARM64; pacman substitutes `$arch` automatically. On regular Arch Linux / Arch Linux ARM rather than Omarchy, use your usual full system upgrade command in place of `omarchy update`.

## Repository configuration

`/etc/pacman.d/seth-reee.conf`:

```ini
[seth-reee]
SigLevel = Required
Server = https://seth-reee.github.io/omarchy-packages/$arch
```

Include it once near the end of `/etc/pacman.conf`:

```ini
Include = /etc/pacman.d/seth-reee.conf
```

The key is available at <https://seth-reee.github.io/omarchy-packages/seth-reee.asc>. Only this repository requires this additional key; existing Arch and Omarchy signing settings are unchanged.

## Automation

A scheduled Actions workflow checks the latest published releases of all five apps every 15 minutes. GitHub can delay scheduled jobs. Each changed package is checked against its release checksums and GitHub asset digest, and its package name, version, and architecture are validated. Packages and repository databases are then signed and deployed together through GitHub Pages. If any verification fails, deployment stops and the previous site stays available.

Nothing rebuilds or republishes when the release manifest is unchanged. Run **Signed package repository** manually for an immediate check, or select **force** to rebuild. A monthly heartbeat commit keeps GitHub's scheduled workflow active during quiet months. The signing private key is stored only in the Actions secret `REPOSITORY_SIGNING_KEY`; the tracked `keys/` directory contains public material only.

## Checks and removal

```bash
pacman-conf --repo seth-reee Server
pacman -Sl seth-reee
pacman -Si seth-reee/tether
```

To stop receiving updates, remove the include line from `/etc/pacman.conf`. Installed apps remain installed. Delete `/etc/pacman.d/seth-reee.conf` if desired. After removing the repository, its trust key can be removed with `sudo pacman-key --delete 186C035DEE6A26BD035AB1D3319FE7C0F23D8AE5`.

Local developer copies of executables or desktop files can override packaged apps. Use `command -v APP` if the launched version differs from `pacman -Q APP`.
