import os, subprocess, re, requests, urllib.parse
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
LINK_FILE = "GIMME-LINKS.txt"
DOWNLOAD_DIR = "downloads"
EXTENSIONS = ('.exe', '.deb', '.msi', '.pkg', '.dmg', '.apk', '.zip', '.7z', '.tar.gz', '.rpm')
VIDEO_SITES = ['youtube.com', 'youtu.be', 'twitter.com', 'tiktok.com', 'instagram.com', 'vimeo.com']

def setup():
    if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR)
    # Clear old downloads to keep repo size healthy
    for f in os.listdir(DOWNLOAD_DIR):
        try: os.remove(os.path.join(DOWNLOAD_DIR, f))
        except: pass

def get_url():
    if not os.path.exists(LINK_FILE): return None
    with open(LINK_FILE, 'r') as f:
        return f.read().strip()

def download_video(url):
    print(f"🎬 Downloading Video: {url}")
    # Using browser impersonation to bypass bot detection
    cmd = [
        'yt-dlp', 
        '--impersonate-browser', 'chrome',
        '--no-playlist',
        '--format', 'best',
        '-o', f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        url
    ]
    subprocess.run(cmd)

def download_direct(url):
    print(f"📥 Downloading Direct: {url}")
    try:
        # Use curl for better reliability on direct links
        filename = url.split('/')[-1].split('?')[0] or "downloaded_file"
        subprocess.run(['curl', '-L', url, '-o', os.path.join(DOWNLOAD_DIR, filename)], check=True)
        return True
    except: return False

def smart_crawl(url):
    print(f"🔍 Crawling Site: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            full_link = urllib.parse.urljoin(url, a['href'])
            if any(full_link.lower().endswith(ext) for ext in EXTENSIONS):
                links.append(full_link)
        
        # Remove duplicates
        links = list(set(links))
        print(f"✅ Found {len(links)} potential files.")
        
        for link in links[:5]: # Limit to 5 files
            download_direct(link)
    except Exception as e:
        print(f"❌ Crawl error: {e}")

def process_splits():
    # Split files > 90MB for GitHub compatibility
    for f in os.listdir(DOWNLOAD_DIR):
        fpath = os.path.join(DOWNLOAD_DIR, f)
        if os.path.isfile(fpath) and os.path.getsize(fpath) > 90 * 1024 * 1024:
            print(f"✂️ Splitting: {f}")
            subprocess.run(['split', '-b', '90M', '-d', '--numeric-suffixes=1', fpath, fpath + "."])
            os.remove(fpath)

def update_readme():
    print("📝 Updating README...")
    table = "| File Name | Size | Link |\n| :--- | :--- | :--- |\n"
    has_split = False
    main_name = ""
    
    files = sorted(os.listdir(DOWNLOAD_DIR))
    if not files:
        table += "| No files found | - | - |\n"
    else:
        for f in files:
            size = f"{os.path.getsize(os.path.join(DOWNLOAD_DIR, f)) / (1024*1024):.1f} MB"
            enc_name = urllib.parse.quote(f)
            url = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY')}/main/downloads/{enc_name}"
            table += f"| {f} | {size} | [Download]({url}) |\n"
            if re.search(r'\.[1-9]$', f):
                has_split = True
                main_name = f.rsplit('.', 1)[0]

    with open('README.md', 'r') as f: content = f.read()
    
    # Update Table
    content = re.sub(r'<!-- TABLE_START -->.*?<!-- TABLE_END -->', 
                    f'<!-- TABLE_START -->\n{table}\n<!-- TABLE_END -->', content, flags=re.DOTALL)
    
    # Update Commands
    l_cmd = f"cat \"downloads/{main_name}\".* > \"{main_name}\"" if has_split else "# No parts to join!"
    w_cmd = f"Get-Content \"downloads/{main_name}\".* -ReadCount 10mb -Encoding Byte | Set-Content \"{main_name}\" -Encoding Byte" if has_split else "# No parts to join!"
    
    content = re.sub(r'<!-- LINUX_CMD_START -->.*?<!-- LINUX_CMD_END -->', f'<!-- LINUX_CMD_START -->\n```bash\n{l_cmd}\n```\n<!-- LINUX_CMD_END -->', content, flags=re.DOTALL)
    content = re.sub(r'<!-- WIN_CMD_START -->.*?<!-- WIN_CMD_END -->', f'<!-- WIN_CMD_START -->\n```powershell\n{w_cmd}\n```\n<!-- WIN_CMD_END -->', content, flags=re.DOTALL)

    with open('README.md', 'w') as f: f.write(content)

if __name__ == "__main__":
    setup()
    url = get_url()
    if url:
        if any(site in url for site in VIDEO_SITES):
            download_video(url)
        elif url.lower().endswith(EXTENSIONS):
            download_direct(url)
        elif re.match(r'^[A-Za-z0-9_-]+/[A-Za-z0-9_-]+$', url):
            subprocess.run(['gh', 'release', 'download', '--repo', url, '--archive', 'zip', '--output', f'{DOWNLOAD_DIR}/repo.zip'])
        else:
            smart_crawl(url)
            
    process_splits()
    update_readme()
