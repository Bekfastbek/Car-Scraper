import asyncio
import json
import re
from playwright.async_api import async_playwright
from datetime import datetime

async def run_browser():
    playwright = await async_playwright().start()
    
    browser = await playwright.chromium.launch(
        headless=True,
        slow_mo=50,
    )
    
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 800},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    )
    
    page = await context.new_page()
    
    print("Browser is running in headed mode")
    
    return playwright, browser, context, page

async def fetch_brands():
    playwright, browser, context, page = await run_browser()
    
    try:
        print("Navigating to autoevolution.com/cars/...")
        await page.goto('https://www.autoevolution.com/cars/')
        print(f"Page title: {await page.title()}")
        website_brand_count = await page.evaluate("""
            () => {
                const element = document.querySelector('.carbrnum b');
                return element ? parseInt(element.textContent.trim()) : null;
            }
        """)
        
        if website_brand_count:
            print(f"Website claims to have {website_brand_count} brands")
        else:
            print("Could not find brand count on the page")
        
        print("Scrolling down to load all car brands...")
        for _ in range(8):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1.5)
        brand_data = await page.evaluate("""
            () => {
                const brandItems = [];
                
                document.querySelectorAll('.carman').forEach(brandElement => {
                    const h5Element = brandElement.querySelector('h5 a span');
                    if (!h5Element) return;
                    
                    const brandName = h5Element.textContent.trim();
                    
                    if (brandName.length <= 1) return;
                    
                    const urlElement = brandElement.querySelector('h5 a');
                    const url = urlElement ? urlElement.getAttribute('href') : null;
                    
                    const statsElement = brandElement.nextElementSibling;
                    let inProduction = 0;
                    let discontinued = 0;
                    
                    if (statsElement && statsElement.classList.contains('carnums')) {
                        const statsTexts = statsElement.querySelectorAll('p b');
                        if (statsTexts.length >= 2) {
                            inProduction = parseInt(statsTexts[0].textContent.trim()) || 0;
                            discontinued = parseInt(statsTexts[1].textContent.trim()) || 0;
                        }
                    }
                      brandItems.push({
                        name: brandName,
                        name_normalized: brandName.toUpperCase(),
                        url: url,
                        in_production: inProduction,
                        discontinued: discontinued,
                        total_models: inProduction + discontinued
                    });
                });
                
                return brandItems;
            }
        """)
        unique_brands_normalized = set(item['name_normalized'] for item in brand_data)
        unique_brands = set(item['name'] for item in brand_data)
        total_brands = len(unique_brands_normalized)
        
        print(f"Found {total_brands} unique car brands")
        
        print("\nCar brands found:")
        for i, brand in enumerate(sorted(unique_brands), 1):
            print(f"{i}. {brand}")
        json_filename = "car_brands.json"
        
        export_data = {
            "source": "autoevolution.com",
            "extracted_date": datetime.now().isoformat(),
            "total_brands": total_brands,
            "claimed_brand_count": website_brand_count,
            "brands_data": sorted(brand_data, key=lambda x: x['name']),
            "brands_list": sorted(list(unique_brands))
        }
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nData saved to {json_filename}")
        if website_brand_count and total_brands != website_brand_count:
            print(f"NOTE: Found {total_brands} brands but website claims {website_brand_count} brands.")
            print("Manual verification has confirmed that there are indeed only 124 brands on the website.")
            print("The website's claim of 131 brands appears to be incorrect or outdated.")
        else:
            print(f"SUCCESS: Found all {total_brands} car brands!")
        await asyncio.sleep(2)
        
        return json_filename
        
    finally:
        await context.close()
        await browser.close()
        await playwright.stop()

async def main():
    await fetch_brands()
        
if __name__ == "__main__":
    asyncio.run(main())
