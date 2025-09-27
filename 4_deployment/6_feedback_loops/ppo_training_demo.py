#!/usr/bin/env python3
import json
from pathlib import Path
import torch
from torch.optim import AdamW
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
)
from peft import LoraConfig, get_peft_model


def train_ppo_model():
    """Train LLM with PPO using trained reward model"""

    model_name = "Qwen/Qwen3-0.6B"

    # Load base model and add LoRA
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.config.pad_token_id = tokenizer.pad_token_id

    # Add LoRA for efficient fine-tuning
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    # Load trained reward model
    reward_tokenizer = AutoTokenizer.from_pretrained("./thumbs_reward_model_final")
    reward_model = AutoModelForSequenceClassification.from_pretrained(
        "./thumbs_reward_model_final"
    )

    # Load training prompts
    with open(Path(__file__).parent / "thumbs_feedback_data.json", "r") as f:
        data = json.load(f)

    prompts = list(set(item["prompt"] for item in data))

    # Setup optimizer
    optimizer = AdamW(model.parameters(), lr=1e-5)

    # Training loop
    for epoch in range(2):
        print(f"Epoch {epoch + 1}/2")

        for prompt in prompts:
            # Format as chat message
            messages = [{"role": "user", "content": prompt}]
            chat_prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )

            inputs = tokenizer(chat_prompt, return_tensors="pt")

            # Generate response
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=True,
                temperature=0.7,
                pad_token_id=tokenizer.pad_token_id,
                return_dict_in_generate=True,
                output_scores=True,
            )

            full_response = tokenizer.decode(
                outputs.sequences[0], skip_special_tokens=True
            )
            response = tokenizer.decode(
                outputs.sequences[0][len(inputs.input_ids[0]) :],
                skip_special_tokens=True,
            )

            # Get reward score
            reward_score = get_reward_score(
                prompt, response, reward_tokenizer, reward_model
            )

            # Simple policy gradient update
            if reward_score > 0:  # Only update on positive rewards
                # Use the chat format for training
                train_inputs = tokenizer(full_response, return_tensors="pt")

                # Forward pass for training
                train_outputs = model(**train_inputs, labels=train_inputs["input_ids"])
                loss = train_outputs.loss

                # Scale loss by reward (higher reward = lower loss)
                scaled_loss = loss * (1.0 - reward_score)

                # Backward pass
                optimizer.zero_grad()
                scaled_loss.backward()
                optimizer.step()

                print(
                    f"Updated model: reward={reward_score:.3f}, loss={scaled_loss.item():.3f}"
                )
            else:
                print(f"Skipped update: reward={reward_score:.3f}")

    # Save the trained model
    model.save_pretrained("./ppo_trained_model")
    tokenizer.save_pretrained("./ppo_trained_model")

    return model


def get_reward_score(
    prompt: str, response: str, reward_tokenizer, reward_model
) -> float:
    """Get reward score from trained reward model"""

    # Format as the reward model expects (prompt + response)
    full_text = f"{prompt} {response}"

    inputs = reward_tokenizer(
        full_text, return_tensors="pt", truncation=True, max_length=512
    )

    with torch.no_grad():
        outputs = reward_model(**inputs)
        reward_score = torch.sigmoid(outputs.logits).item()

    return reward_score


def test_trained_model():
    """Test the PPO-trained model"""

    # Load base and trained models
    base_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
    base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B")
    if base_tokenizer.pad_token is None:
        base_tokenizer.pad_token = base_tokenizer.eos_token

    trained_tokenizer = AutoTokenizer.from_pretrained("./ppo_trained_model")
    trained_model = AutoModelForCausalLM.from_pretrained("./ppo_trained_model")

    test_prompts = [
        "How do I reset my password?",
        "Explain machine learning",
        "What are your pricing options?",
    ]

    for prompt in test_prompts:
        print(f"\nPrompt: {prompt}")

        # Base model response
        base_messages = [{"role": "user", "content": prompt}]
        base_chat_prompt = base_tokenizer.apply_chat_template(
            base_messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        base_inputs = base_tokenizer(base_chat_prompt, return_tensors="pt")

        with torch.no_grad():
            base_outputs = base_model.generate(
                **base_inputs,
                max_new_tokens=50,
                do_sample=True,
                temperature=0.7,
                pad_token_id=base_tokenizer.pad_token_id,
            )
        base_response = base_tokenizer.decode(
            base_outputs[0][len(base_inputs.input_ids[0]) :], skip_special_tokens=True
        )

        # Trained model response
        trained_messages = [{"role": "user", "content": prompt}]
        trained_chat_prompt = trained_tokenizer.apply_chat_template(
            trained_messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        trained_inputs = trained_tokenizer(trained_chat_prompt, return_tensors="pt")

        with torch.no_grad():
            trained_outputs = trained_model.generate(
                **trained_inputs,
                max_new_tokens=50,
                do_sample=True,
                temperature=0.7,
                pad_token_id=trained_tokenizer.pad_token_id,
            )
        trained_response = trained_tokenizer.decode(
            trained_outputs[0][len(trained_inputs.input_ids[0]) :],
            skip_special_tokens=True,
        )

        print(f"Base:    {base_response}")
        print(f"Trained: {trained_response}")


if __name__ == "__main__":
    model = train_ppo_model()
    test_trained_model()
