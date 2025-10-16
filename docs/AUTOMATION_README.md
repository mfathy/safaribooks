# 🚀 O'Reilly Books Automation

Automated downloading and organization of O'Reilly books by your favorite skills.

## ✨ Features

- **🎯 Skill-Based Organization**: Books automatically organized in skill-specific folders
- **📚 Smart Book Discovery**: Uses O'Reilly's API to find relevant books for each skill
- **🔄 Resume Capability**: Interrupted downloads can be resumed automatically
- **⚡ Concurrent Downloads**: Configurable parallel downloading for faster processing
- **📊 Progress Tracking**: Detailed logging and progress files
- **🛡️ Error Handling**: Robust error handling with retry mechanisms
- **⚙️ Configurable**: Extensive configuration options via JSON file

## 🏃‍♂️ Quick Start

### 1. Prerequisites
- Python 3.7+
- Valid O'Reilly Learning subscription
- Authentication cookies set up (see `COOKIE_SETUP.md`)

### 2. Simple Usage

```bash
# Interactive quick start
python quick_download.py

# Or direct command
python automate_skill_downloads.py
```

### 3. Download Specific Skills

```bash
python automate_skill_downloads.py --skills "Python" "Machine Learning" "AI & ML"
```

### 4. Test Run (Recommended First)

```bash
python automate_skill_downloads.py --dry-run
```

## 📁 Output Structure

```
books_by_skills/
├── Python/
│   ├── Learning Python (9781449355739)/
│   │   ├── Learning Python.epub
│   │   └── OEBPS/
│   └── Python Cookbook (9781449340377)/
├── Machine Learning/
│   ├── Hands-On Machine Learning (9781492032649)/
│   └── Pattern Recognition and Machine Learning (9780387310732)/
└── AI & ML/
    └── ...
```

## ⚙️ Configuration

Edit `download_config.json` to customize:

```json
{
  "max_books_per_skill": 30,
  "download_delay": 3,
  "max_workers": 2,
  "epub_format": "enhanced"
}
```

## 📋 Scripts Overview

| Script | Purpose |
|--------|---------|
| `automate_skill_downloads.py` | Main automation script |
| `quick_download.py` | Interactive simplified interface |
| `download_config.json` | Configuration file |
| `my_favorite_skills.txt` | Your skills list (298 skills included) |

## 🎯 Common Use Cases

### Download Everything
```bash
python automate_skill_downloads.py
```

### Focus on AI/ML
```bash
python automate_skill_downloads.py --skills "AI & ML" "Machine Learning" "Deep Learning" "Data Science"
```

### Programming Languages
```bash
python automate_skill_downloads.py --skills "Python" "Java" "JavaScript" "Go" "Rust"
```

### DevOps & Cloud
```bash
python automate_skill_downloads.py --skills "AWS" "Docker" "Kubernetes" "DevOps" "Terraform"
```

## 📊 Progress & Results

- **`download_progress.json`**: Current download state
- **`download_results.json`**: Final summary with statistics
- **`skill_downloader.log`**: Detailed execution log

## 🔧 Advanced Options

```bash
# Custom limits
python automate_skill_downloads.py --max-books 50 --max-pages 5

# High performance
python automate_skill_downloads.py --workers 4 --format dual

# Conservative approach
python automate_skill_downloads.py --workers 1 --max-books 10
```

## 🛠️ Troubleshooting

### Rate Limiting
```bash
# Reduce concurrency and increase delays
python automate_skill_downloads.py --workers 1 --max-books 5
```

### Authentication Issues
- Ensure `cookies.json` is properly configured
- Check O'Reilly subscription status

### Disk Space
- Monitor available space
- Reduce `max_books_per_skill` in config

### Network Issues
- Script automatically retries failed downloads
- Check internet connection stability

## 📖 Detailed Documentation

- **`AUTOMATION_GUIDE.md`**: Comprehensive usage guide
- **`COOKIE_SETUP.md`**: Authentication setup instructions

## 🎉 Example Results

After running the automation with your 298 favorite skills, you'll have:

- 📚 Thousands of books organized by skill
- 📁 Clean folder structure for easy browsing
- 📊 Detailed statistics of downloaded content
- 🔄 Ability to resume/add more books anytime

## 💡 Tips

1. **Start Small**: Test with a few skills first
2. **Monitor Progress**: Check logs during large downloads
3. **Resume Capability**: Interruptions are handled gracefully
4. **Customize**: Adjust config for your needs and preferences

---

**Ready to get started?** Run `python quick_download.py` for an interactive setup!
