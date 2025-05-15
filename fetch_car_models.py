import asyncio
import json
import os
import aiohttp
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from datetime import datetime

IMAGES_DIR = "car_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

async def download_image(session, image_url, save_path):
    try:
        async with session.get(image_url) as response:
            if response.status == 200:
                content = await response.read()
                with open(save_path, "wb") as f:
                    f.write(content)
                print(f"Saved image to {save_path}")
                return save_path
            else:
                print(f"Failed to download image {image_url}, status: {response.status}")
                return None
    except Exception as e:
        print(f"Error downloading {image_url}: {e}")
        return None

async def process_brands_batch(batch, browser, playwright):
    results = []
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        contexts = []
        
        for brand_data in batch:
            brand_name = brand_data["name"]
            brand_url = brand_data["url"]
            
            print(f"Queuing brand: {brand_name} at {brand_url}")
            brand_folder = os.path.join(IMAGES_DIR, brand_name.replace(" ", "_").replace("/", "_"))
            os.makedirs(brand_folder, exist_ok=True)
            
            context = await browser.new_context(
                **playwright.devices['iPhone 13 Pro Max']
            )
            contexts.append(context)
            
            task = asyncio.create_task(process_brand_page(brand_data, context, session))
            tasks.append((brand_data, task))
        
        for (brand_data, task), context in zip(tasks, contexts):
            try:
                result = await task
                results.append(result)
            except Exception as e:
                print(f"Error processing {brand_data['name']}: {e}")
                results.append({
                    "brand_name": brand_data["name"],
                    "brand_url": brand_data["url"],
                    "error": str(e)
                })
            finally:
                await context.close()
    
    return results

async def process_brand_page(brand_data, context, session):
    brand_name = brand_data["name"]
    brand_url = brand_data["url"]
    brand_folder = os.path.join(IMAGES_DIR, brand_name.replace(" ", "_").replace("/", "_"))
    
    try:
        page = await context.new_page()
        await page.goto(brand_url, wait_until="networkidle", timeout=60000)
        car_models_data = await page.evaluate("""
            () => {
                const carModels = [];
                
                document.querySelectorAll('a[title*="specs and photos"]').forEach(nameElement => {
                    const modelName = nameElement.getAttribute('title').replace(' specs and photos', '').trim();
                    const modelUrl = nameElement.getAttribute('href');
                    
                    let imageUrl = null;
                    const imgElement = nameElement.querySelector('img') || 
                                      (nameElement.parentElement ? nameElement.parentElement.querySelector('img') : null);
                    
                    if (imgElement) {
                        imageUrl = imgElement.getAttribute('src');
                        if (!imageUrl || imageUrl.includes('blank.gif')) {
                            imageUrl = imgElement.getAttribute('data-src') || null;
                        }
                    }
                    
                    let productionYears = null;
                    const parentElement = nameElement.closest('.container2') || nameElement.parentElement;
                    const yearElement = parentElement ? parentElement.querySelector('.years, .semra') : null;
                    if (yearElement) {
                        productionYears = yearElement.textContent.trim();
                    }
                    
                    carModels.push({
                        name: modelName,
                        url: modelUrl,
                        image_url: imageUrl,
                        production_years: productionYears
                    });
                });
                
                return carModels;
            }
        """)
        
        unique_models = {}
        for model in car_models_data:
            if model.get("url") and model["url"] not in unique_models:
                unique_models[model["url"]] = model
        
        car_models_data = list(unique_models.values())
        print(f"Found {len(car_models_data)} unique models for {brand_name} after removing duplicates")
        
        models_with_images = []
        image_download_tasks = []
        
        for model in car_models_data:
            if model.get("image_url"):
                safe_model_name = model['name'].replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
                
                image_filename = f"{safe_model_name}.jpg"
                image_path = os.path.join(brand_folder, image_filename)
                
                task = asyncio.create_task(download_image(session, model["image_url"], image_path))
                image_download_tasks.append((model, task))
        
        for model, task in image_download_tasks:
            saved_path = await task
            if saved_path:
                model["screenshot_path"] = os.path.relpath(saved_path, os.getcwd())
                models_with_images.append(model)
        
        return {
            "brand_name": brand_name,
            "brand_url": brand_url,
            "models_count": len(car_models_data),
            "models_with_images": len(models_with_images),
            "car_models": car_models_data
        }
        
    except Exception as e:
        print(f"Error processing {brand_name}: {e}")
        return {
            "brand_name": brand_name,
            "brand_url": brand_url,
            "error": str(e)
        }

async def fetch_car_models(brands_json_file="car_brands.json"):
    try:
        existing_results = {}
        if os.path.exists("car_models.json"):
            try:
                with open("car_models.json", "r", encoding="utf-8") as f:
                    existing_results = json.load(f)
                print("Loaded existing car_models.json")
            except Exception as e:
                print(f"Error loading existing car_models.json: {e}")
                existing_results = {}
        
        with open(brands_json_file, "r", encoding="utf-8") as f:
            brands_data = json.load(f)
        
        brands = brands_data["brands_data"]
        print(f"Loaded {len(brands)} brands from {brands_json_file}")
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            slow_mo=50,
        )
        
        try:
            batch_size = 12  # Change this to control the number of concurrent brands
            all_results = existing_results.get("brand_models", [])
            processed_brand_names = {brand["brand_name"] for brand in all_results if "brand_name" in brand}
            
            brands_to_process = [brand for brand in brands if brand["name"] not in processed_brand_names]
            print(f"{len(brands_to_process)} brands to process out of {len(brands)} total brands")
            
            for i in range(0, len(brands_to_process), batch_size):
                batch = brands_to_process[i:i+batch_size]
                print(f"\nProcessing batch {i//batch_size + 1} of {(len(brands_to_process) + batch_size - 1) // batch_size}")
                print(f"Batch contains {len(batch)} brands: {', '.join([brand['name'] for brand in batch])}")
                start_time = datetime.now()
                print(f"Starting batch at: {start_time.strftime('%H:%M:%S')}")
                
                batch_results = await process_brands_batch(batch, browser, playwright)
                
                end_time = datetime.now()
                duration = end_time - start_time
                print(f"Completed batch in: {duration.total_seconds():.2f} seconds")
                
                brand_results_map = {}
                
                for result in all_results:
                    if "brand_name" in result:
                        brand_results_map[result["brand_name"]] = result
                
                for result in batch_results:
                    if "brand_name" in result:
                        brand_results_map[result["brand_name"]] = result
                
                all_results = list(brand_results_map.values())
                print(f"Total unique brands processed so far: {len(all_results)}")
                
                car_models_data = {
                    "extraction_date": datetime.now().isoformat(),
                    "total_brands_processed": len(all_results),
                    "brand_models": all_results
                }
                
                with open("car_models.json", "w", encoding="utf-8") as f:
                    json.dump(car_models_data, f, indent=2, ensure_ascii=False)
                print(f"Updated car_models.json with {len(batch_results)} new brands")
                
                await asyncio.sleep(1)
            
            total_models = sum(result.get("models_count", 0) for result in all_results if "models_count" in result)
            total_models_with_images = sum(result.get("models_with_images", 0) for result in all_results if "models_with_images" in result)
            print(f"\nSummary:")
            print(f"- Brands processed: {len(all_results)}")
            print(f"- Total car models found: {total_models}")
            print(f"- Models with downloaded images: {total_models_with_images}")            
        finally:
            await browser.close()
            await playwright.stop()
        
        return "car_models.json"
        
    except Exception as e:
        print(f"Error in fetch_car_models: {e}")
        return None

async def main():
    await fetch_car_models()

if __name__ == "__main__":
    asyncio.run(main())
