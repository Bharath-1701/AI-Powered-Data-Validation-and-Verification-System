import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor
import time
from tqdm import tqdm

# Define the LLM Foundry token for your API requests
LLMFOUNDRY_TOKEN = "Your_key"

# Function to interact with the first model
def chat_with_llm_model1(user_input):
    
    response = requests.post(
        "https://llmfoundry.straive.com/azure/openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-05-01-preview",
        headers={"Authorization": f"Bearer {LLMFOUNDRY_TOKEN}:Muthu_bot"},
        json={"messages": [{"role": "user", "content": user_input}]},
    )
    
    if response.status_code == 200:
        response_json = response.json()
        answer = response_json['choices'][0]['message']['content']
        return answer
    else:
        return f"Error: {response.status_code} - {response.text}"

# Function to interact with the second model
def chat_with_llm_model2(user_input):
    
    response = requests.post(
        "https://llmfoundry.straive.com/anthropic/v1/messages",
        headers={"Authorization": f"Bearer {LLMFOUNDRY_TOKEN}:Muthu_bot"},
        json={"model": "claude-3-haiku-20240307", "max_tokens": 1000, "messages": [{"role": "user", "content": user_input}]},
    )
    
    if response.status_code == 200:
        response_json = response.json()
        answer = response_json['content'][0]['text']
        return answer
    else:
        return f"Error: {response.status_code} - {response.text}"

# Load the Excel file and the specific sheet
file_path = r'D:\python_test\test\city_name\city_name.xlsx'
sheet_name = 'Cosmo Input Report'
print("Loading Excel file.")
df = pd.read_excel(file_path, sheet_name=sheet_name)

# Load the prompt from the text file
print("Loading prompt from text file.")
with open(r'D:\python_test\test\city_name\prompt.txt', 'r') as file:
    prompt_template = file.read()

# Check for result columns and add them if they don't exist
for col in ['Result_Model1', 'Result_Model2', 'City_Check']:
    if col not in df.columns:
        df[col] = None
        
MAX_THREADS = 5
matches = 0
# Function to process each row and update results for both models
def process_row(index, row):
    main_city = row['Source City name']
    description = row['Description']
    prompt = prompt_template.format(main_city=main_city, description=description)

    result_model1 = chat_with_llm_model1(prompt)
    result_model2 = chat_with_llm_model2(prompt)
    time.sleep(2)
    
    city_name_lower = main_city.lower()
    description_lower = description.lower()
    city_check = (city_name_lower in description_lower) or (f"{city_name_lower}'s" in description_lower)
    
    city_check_result = "City name available and matching" if city_check else "City name not available or mismatched"
    
    return index, result_model1, result_model2, city_check_result

# Parallel processing of the rows
total_rows = len(df)
print("Starting parallel processing of rows.")
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = {executor.submit(process_row, i, row): i for i, row in df.iterrows()}
    for future in tqdm(futures, total=total_rows, desc="Processing Rows"):
        i, result_model1, result_model2, city_check_result = future.result()
        df.at[i, 'Result_Model1'] = result_model1
        df.at[i, 'Result_Model2'] = result_model2
        df.at[i, 'City_Check'] = city_check_result
    print("finished processing all rows")

def verify_model_results(row):
    expected_result = "a. City name available and main city matching"
    city_check_phrase = "City name available and matching"
    model1_status = "Correct" if row['Result_Model1'] == expected_result else "Result_Model1 is wrong"
    model2_status = "Correct" if row['Result_Model2'] == expected_result else "Result_Model2 is wrong"
    overall_status = ""

    if row['City_Check'] == city_check_phrase:
        if row['Result_Model1'] != expected_result:
            overall_status += model1_status
        if row['Result_Model2'] != expected_result:
            overall_status += " and " + model2_status if overall_status else model2_status
    else:
        # If City_Check is not as expected, no comparison is required with model results.
        overall_status = "City not matching, no need to check models."
    
    return overall_status if overall_status else "Correct"

# Ensure the fourth column exists
if 'Result_Check' not in df.columns:
    df['Result_Check'] = None

print("Verifying model results and updating 'Result_Check' column.")
df['Result_Check'] = df.apply(verify_model_results, axis=1)

# Calculate summary information
correct_count = df['Result_Check'].value_counts().get("Correct", 0)
wrong_model1_count = df['Result_Check'].str.contains("Result_Model1 is wrong").sum()
wrong_model2_count = df['Result_Check'].str.contains("Result_Model2 is wrong").sum()
no_check_needed_count = df['Result_Check'].str.contains("City not matching").sum()

# Output summary information
print(f"Total rows processed: {len(df)}")
print(f"Correct matches: {correct_count}")
print(f"Rows where Result_Model1 is wrong: {wrong_model1_count}")
print(f"Rows where Result_Model2 is wrong: {wrong_model2_count}")
print(f"Rows where model comparison was not needed: {no_check_needed_count}")

# Save the modified DataFrame back to Excel
print("Saving the results to Excel.")
df.to_excel(r'D:\python_test\test\city_name\processed_city_name.xlsx', sheet_name=sheet_name, index=False)
print("Processing completed and file saved.")
