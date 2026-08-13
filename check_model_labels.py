from transformers import pipeline

# Test loading a valid emotion model
model_name = "trpakov/vit-face-expression"
print(f"Loading {model_name}...")
classifier = pipeline("image-classification", model=model_name, top_k=10)
print("Model loaded! Labels:")
print(classifier.model.config.id2label)
