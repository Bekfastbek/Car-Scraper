# Car Scraper

A comprehensive web scraper for automotive data that extracts detailed car information from AutoEvolution.com, including brands, models, generations, and images.

## Installation

### Prerequisites
- Python 3
- Required packages (install via pip):

```bash
pip install -r requirements.txt
```

### Required Dependencies
```
playwright
aiohttp
```

### Playwright Setup
After installing playwright, you need to install browser binaries:
```bash
playwright install chromium
```

## Usage

### **Quick Start - Full Scraping**

Run the complete scraping process (brands → models → generations):

```bash
python main.py
```

### Batch Size
Modify the batch size relative to your cpu threads in `fetch_car_models.py`:

NOTE: The scraper is extremely resource intensive due to multithreading, you can reduce the resource usage by reducing batch size at the cost of longer waiting time
```python
batch_size = 12  # Number of concurrent brands
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes thoroughly
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.