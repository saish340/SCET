#!/usr/bin/env python3
"""
SCET Model Training Script
Trains the ML model from CSV dataset
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.ml_model.trainer import get_trainer
from app.config import get_settings

settings = get_settings()


async def main():
    """Main training function"""
    print("=" * 60)
    print("SCET - Smart Copyright Expiry Tag")
    print("ML Model Training from CSV Dataset")
    print("=" * 60)
    
    # Get trainer instance
    trainer = get_trainer()
    
    # Default CSV path
    csv_path = settings.DATA_PATH / "training_data.csv"
    
    # Check for command line argument
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    
    print(f"\nCSV Path: {csv_path}")
    
    if not csv_path.exists():
        print(f"\n❌ Error: CSV file not found at {csv_path}")
        print("Usage: python train_model.py [path_to_csv]")
        return
    
    print("\n📊 Starting training...")
    
    # Run training
    result = await trainer.train_from_csv(str(csv_path))
    
    print("\n" + "=" * 60)
    if result.get("success"):
        print("✅ Training Complete!")
        print(f"   Samples Processed: {result.get('samples_processed', 0)}")
        print(f"   Samples Skipped:   {result.get('samples_skipped', 0)}")
        
        stats = result.get("model_stats", {})
        print(f"\n📈 Model Statistics:")
        print(f"   Total Training Samples: {stats.get('training_samples', 0)}")
        print(f"   Feature Count:          {stats.get('feature_count', 0)}")
        print(f"   Last Trained:           {stats.get('last_trained', 'N/A')}")
        
        if stats.get('rolling_accuracy'):
            print(f"   Rolling Accuracy:       {stats.get('rolling_accuracy', 0):.2%}")
    else:
        print(f"❌ Training Failed: {result.get('error', 'Unknown error')}")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
