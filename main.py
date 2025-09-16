import asyncio
import os
import sys
import json
from datetime import datetime
from fetch_brands import fetch_brands
from fetch_car_models import fetch_car_models



def cleanup_car_models_data(file_path="car_models.json"):
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "brand_models" not in data:
            return False
        total_brands = len(data["brand_models"])
        total_models_before = sum(
            len(brand.get("car_models", [])) 
            for brand in data["brand_models"]
        )
        for brand in data["brand_models"]:
            if "car_models" not in brand:
                continue
            unique_models = {}
            for model in brand.get("car_models", []):
                if "url" in model and model["url"]:
                    if model["url"] not in unique_models:
                        unique_models[model["url"]] = model
            brand["car_models"] = list(unique_models.values())
            brand["models_count"] = len(brand["car_models"])
            brand["models_with_images"] = sum(1 for model in brand["car_models"] if "local_image_path" in model)
        total_models_after = sum(
            len(brand.get("car_models", [])) 
            for brand in data["brand_models"]
        )
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        duplicates_removed = total_models_before - total_models_after
        return True
    except Exception as e:
        print(f"Error during cleanup: {e}")
        return False



async def run_full_scraper():
    start_time = datetime.now()
    try:
        brands_file = await fetch_brands()
        if not brands_file or not os.path.exists(brands_file):
            print(f"Error: Brands file not generated or not found at {brands_file}")
            return False
        await asyncio.sleep(2)
        models_file = await fetch_car_models(brands_file)
        if not models_file or not os.path.exists(models_file):
            print(f"Error: Models file not generated or not found at {models_file}")
            return False
        cleanup_success = cleanup_car_models_data(models_file)
        if not cleanup_success:
            print(f"Error: Cleanup process failed for {models_file}")
            return False
        end_time = datetime.now()
        duration = end_time - start_time
        return True
    except Exception as e:
        print(f"Error during scraping process: {e}")
        return False



def main():
    print("Starting...")
    success = asyncio.run(run_full_scraper())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
