# demo.py — Run this to verify everything works
import os
from RAG import rag_manager

# 1. Create and Ingest a sample text file
sample_file = "sample.txt"
with open(sample_file, "w", encoding="utf-8") as f:
    f.write("""
    The MSMED Act 2006 Section 15 states that buyers must pay MSMEs within 45 days.
    If payment is delayed, Section 16 mandates compound interest at 3x the RBI bank rate.
    The current RBI bank rate is 6.5%, so the penalty rate is 19.5% per annum.
    MSME Samadhaan is an online portal for filing arbitration cases.
    """)

print("Ingesting sample document...")
result = rag_manager.ingest(sample_file, user_id="user_001")
print("Ingest result:", result)
# Expected: {'status': 'success', 'chunks_added': 1}

# 2. Retrieve relevant context
print("\nRetrieving context for query: 'What is the penalty interest rate?'")
context = rag_manager.retrieve("What is the penalty interest rate?", user_id="user_001")
print("\n--- Retrieved Context ---")
print(context)

# Clean up temporary sample file
if os.path.exists(sample_file):
    os.remove(sample_file)
