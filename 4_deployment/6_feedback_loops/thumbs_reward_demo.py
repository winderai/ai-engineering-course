#!/usr/bin/env python3
import json
from pathlib import Path
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from trl.trainer.reward_config import RewardConfig
from trl.trainer.reward_trainer import RewardTrainer


def load_thumbs_feedback_data():
    """Load thumbs up/down feedback data and convert to preference pairs"""
    with open(Path(__file__).parent / "thumbs_feedback_data.json", "r") as f:
        data = json.load(f)

    # Group responses by prompt to create preference pairs
    prompt_groups = {}
    for item in data:
        prompt = item["prompt"]
        if prompt not in prompt_groups:
            prompt_groups[prompt] = {"positive": [], "negative": []}

        if item["rating"] == 1:
            prompt_groups[prompt]["positive"].append(item["response"])
        else:
            prompt_groups[prompt]["negative"].append(item["response"])

    # Create preference pairs from thumbs up/down data
    preference_pairs = []
    for prompt, responses in prompt_groups.items():
        # Create pairs between each positive and negative response
        for chosen in responses["positive"]:
            for rejected in responses["negative"]:
                preference_pairs.append(
                    {"prompt": prompt, "chosen": chosen, "rejected": rejected}
                )

    dataset_dict = {
        "prompt": [pair["prompt"] for pair in preference_pairs],
        "chosen": [pair["chosen"] for pair in preference_pairs],
        "rejected": [pair["rejected"] for pair in preference_pairs],
    }

    dataset = Dataset.from_dict(dataset_dict)
    print(f"✅ Created {len(dataset)} preference pairs from thumbs feedback")
    return dataset


def train_thumbs_reward_model(model_save_path: str):
    """Train a reward model from thumbs up/down feedback"""

    print("👍 Training Reward Model from Thumbs Feedback")
    print("=" * 40)

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

    # Convert thumbs data to preference pairs
    dataset = load_thumbs_feedback_data()

    # RewardConfig extends TrainingArguments with reward-specific settings
    training_args = RewardConfig(
        output_dir="./thumbs_reward_model",
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        warmup_steps=20,
        logging_steps=5,
        save_steps=100,
        eval_strategy="no",
        save_total_limit=1,
        remove_unused_columns=False,
        report_to=[],
        learning_rate=5e-6,  # Lower learning rate for stability with smaller dataset
        weight_decay=0.01,
    )

    # RewardTrainer handles preference pair training with Bradley-Terry loss
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


def test_thumbs_reward_model(model_path):
    """Test the reward model trained from thumbs feedback"""

    print("\n🧪 Testing Thumbs Reward Model")
    print("=" * 30)

    # Load the fine-tuned reward model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSequenceClassification.from_pretrained(model_path)

    # Test with new examples not seen during training
    test_cases = [
        {
            "prompt": "What is artificial intelligence?",
            "good": "Artificial Intelligence (AI) is technology that enables machines to simulate human intelligence, including learning, reasoning, and problem-solving. It encompasses machine learning, natural language processing, and computer vision.",
            "bad": "AI is smart computers.",
        },
        {
            "prompt": "How do I contact support?",
            "good": "You can contact support in several ways: 1) Email us at support@company.com 2) Use the chat widget on our website 3) Call us at 1-800-SUPPORT during business hours (9 AM - 5 PM EST) 4) Submit a ticket through your account dashboard.",
            "bad": "Email support.",
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['prompt']}")

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

        print(f"Detailed response reward: {good_reward:.3f}")
        print(f"Brief response reward: {bad_reward:.3f}")
        print(f"Prefers detailed response: {good_reward > bad_reward}")


if __name__ == "__main__":
    import torch

    model_path = "./thumbs_reward_model_final"
    train_thumbs_reward_model(model_path)
    test_thumbs_reward_model(model_path)
