import os
import shutil
import hashlib
import zipfile
import xml.etree.ElementTree as ET

def create_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def zip_directory(path, zip_name):
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as ziph:
        for root, dirs, files in os.walk(path):
            for file in files:
                # Avoid zipping git files or existing zips
                if '.git' in root or file.endswith('.zip'):
                    continue
                ziph.write(os.path.join(root, file), 
                           os.path.relpath(os.path.join(root, file), 
                           os.path.join(path, '..')))

# Setup paths
repo_root = os.getcwd()
zips_path = os.path.join(repo_root, 'zips')
addons = ['plugin.video.liberator', 'repository.liberator']

# Ensure zips folder exists
if not os.path.exists(zips_path):
    os.makedirs(zips_path)

# Create the master addons.xml
root_xml = ET.Element("addons")

for addon_id in addons:
    addon_path = os.path.join(repo_root, addon_id)
    xml_path = os.path.join(addon_path, 'addon.xml')
    
    if os.path.exists(xml_path):
        # 1. Parse version for filename
        tree = ET.parse(xml_path)
        version = tree.getroot().get('version')
        
        # 2. Add to master XML
        root_xml.append(tree.getroot())
        
        # 3. Create addon-specific zip folder
        dest_folder = os.path.join(zips_path, addon_id)
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
            
        # 4. Zip it up
        zip_name = f"{addon_id}-{version}.zip"
        zip_directory(addon_path, os.path.join(dest_folder, zip_name))
        print(f"Created zip for {addon_id} version {version}")

# Save master XML
xml_content = ET.tostring(root_xml, encoding='utf-8', method='xml')
with open(os.path.join(zips_path, 'addons.xml'), 'wb') as f:
    f.write(b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + xml_content)

# Save MD5
md5_hash = create_md5(os.path.join(zips_path, 'addons.xml'))
with open(os.path.join(zips_path, 'addons.xml.md5'), 'w') as f:
    f.write(md5_hash)

print("Repository generation complete!")