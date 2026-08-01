# Project Rules & Guidelines for Liberator

## Deployment Process for Liberator Addon & Repository
When asked to deploy Liberator:
1. Increment the version number in `addon.xml`.
2. Add a corresponding release entry at the top of `resources/text/changelog.txt`.
3. Merge feature branch into `main` and push `main` to `https://github.com/Karhugit/plugin.video.liberator.git`.
4. Copy/sync updated files into `D:\Python Coding\liberator-repo\plugin.video.liberator`.
5. Run `python create_repository.py` inside `D:\Python Coding\liberator-repo` to regenerate `plugin.video.liberator-<version>.zip`, `addons.xml`, and `addons.xml.md5`.
6. Commit and push the distribution repository `https://github.com/Karhugit/liberator-repo.git` (`main` branch).
