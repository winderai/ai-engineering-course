#!/bin/bash

correct=0
total=0

for i in {1..10}; do
  response=$(ollama run qwen3:1.7b --think=false "How many r's in strawberry? Answer with just the number.")
  
  echo "Response $i: $response"
  
  if [[ "$response" == *"3"* ]]; then
    ((correct++))
  fi
  ((total++))
done

echo "Accuracy: $correct/$total = $(echo "scale=2; $correct/$total*100" | bc)%"