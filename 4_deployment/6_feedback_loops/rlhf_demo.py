#!/usr/bin/env python3
import json
from pathlib import Path
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from trl.trainer.reward_config import RewardConfig
from trl.trainer.reward_trainer import RewardTrainer


def load_preference_data():
    """Load preference data from JSON file"""
    with open(Path(__file__).parent / "preference_data.json", "r") as f:
        data = json.load(f)

    dataset_dict = {
        "prompt": [item["prompt"] for item in data],
        "chosen": [item["chosen"] for item in data],
        "rejected": [item["rejected"] for item in data],
    }

    dataset = Dataset.from_dict(dataset_dict)
    print(f"✅ Loaded {len(dataset)} preference pairs")
    return dataset


def train_reward_model(model_save_path: str):
    """Train a reward model using TRL and Qwen3"""

    print("🏋️ Training Reward Model with TRL")
    print("=" * 30)

    model_name = "Qwen/Qwen3-0.6B"

    # Load tokenizer and set padding token for batch processing
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model as sequence classifier with single output (reward score)
    # ignore_mismatched_sizes handles classification head dimension mismatch
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=1, ignore_mismatched_sizes=True
    )
    model.config.pad_token_id = tokenizer.pad_token_id

    dataset = load_preference_data()

    # RewardConfig extends TrainingArguments with reward-specific settings
    training_args = RewardConfig(
        output_dir="./reward_model",
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        warmup_steps=50,
        logging_steps=5,
        save_steps=100,
        eval_strategy="no",
        save_total_limit=1,
        remove_unused_columns=False,
        report_to=[],
        learning_rate=1e-5,
        weight_decay=0.01,
    )

    trainer = RewardTrainer(
        args=training_args,
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset,
    )

    print("🚀 Starting training...")
    trainer.train()

    trainer.save_model(model_save_path)
    tokenizer.save_pretrained(model_save_path)

    print("✅ Training completed!")


def test_reward_model(model_path):
    """Test the trained reward model"""

    print("\n🧪 Testing Reward Model")
    print("=" * 25)

    # Load the fine-tuned reward model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)

    # Test cases
    test_cases = [
        {
            "prompt": "What is Python?",
            "good": "Python is a high-level programming language known for its simple syntax and readability. It's widely used for web development, data science, and automation.",
            "bad": "Python is a programming language.",
        }
    ]

    for test in test_cases:
        print(f"Prompt: {test['prompt']}")

        # Combine prompt with response for full context (matches training format)
        good_text = f"{test['prompt']} {test['good']}"
        bad_text = f"{test['prompt']} {test['bad']}"

        # Tokenize the full text sequences
        good_input = tokenizer(
            good_text, return_tensors="pt", truncation=True, max_length=512
        )
        bad_input = tokenizer(
            bad_text, return_tensors="pt", truncation=True, max_length=512
        )

        # Get reward scores from the model's classification head
        with torch.no_grad():
            good_reward = model(**good_input).logits.item()
            bad_reward = model(**bad_input).logits.item()

        print(f"Good response reward: {good_reward:.3f}")
        print(f"Bad response reward: {bad_reward:.3f}")
        print(f"Preference correct: {good_reward > bad_reward}")


if __name__ == "__main__":
    import torch

    model_path = "./reward_model_final"
    train_reward_model(model_path)
    test_reward_model(model_path)
