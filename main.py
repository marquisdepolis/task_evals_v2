import json
import pandas as pd
from scraper import scrape_content
from router import get_llm_response
from tqdm import tqdm
from dotenv import load_dotenv
from difflib import SequenceMatcher

load_dotenv()

def calculate_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def process_excel(input_file, output_file, llm_choices, system_messages, temperatures, group_by_link=False):
    """
    Process the combined DataFrame, query LLMs, and save results to a new Excel file.

    Args:
    input_file (str): Path to the input Excel file.
    output_file (str): Path to the output Excel file.
    llm_choices (dict): Dictionary of LLM choices to use.
    system_messages (dict): Dictionary of system messages to use.
    temperatures (dict): Dictionary of temperatures to use for each LLM.
    """
    df = pd.read_excel(input_file)

    # Ensure required columns exist
    required_columns = ['Term', 'Questions', 'Link', 'AnswerKey']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"Input file must contain columns: {', '.join(required_columns)}")

    # Create columns for results and similarity scores
    for llm in llm_choices.keys():
        for msg_type in system_messages.keys():
            df[f'Result_{llm}_{msg_type}'] = ''
            df[f'Similarity_{llm}_{msg_type}'] = 0.0

    if group_by_link:
        # Group by Link, process up to 5 questions together
        grouped = df.groupby('Link')
        for link, group in tqdm(grouped, desc="Processing Links"):
            process_group(group, link, llm_choices, system_messages, temperatures)
    else:
        # Process each row individually
        for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing Rows"):
            process_row(row, llm_choices, system_messages, temperatures)

    # Reorder columns
    column_order = ['Term', 'Questions', 'Link', 'AnswerKey']
    for llm in llm_choices.keys():
        for msg_type in system_messages.keys():
            column_order.extend([f'Result_{llm}_{msg_type}', f'Similarity_{llm}_{msg_type}'])
    df = df[column_order]

    # Save the results to a new Excel file
    df.to_excel(output_file, index=False)
    print(f"Processing complete. Results saved to {output_file}")

def process_group(group, link, llm_choices, system_messages, temperatures):
    try:
        # Scrape content from the link
        scraped_content = scrape_content(link)
        context = scraped_content['content']

        # Prepare questions and answer keys
        questions = []
        answer_keys = []
        for _, row in group.iterrows()[:5]:  # Limit to 5 questions per link
            questions.extend(row['Questions'].split('|'))
            answer_keys.extend(row['AnswerKey'].split('|'))

        # Create the full prompt with multiple questions
        full_prompt = f"Context: {context}\n\nQuestions:\n"
        for i, question in enumerate(questions, 1):
            full_prompt += f"{i}. {question.strip()}\n"

        # Query each LLM with each system message
        for llm, model in llm_choices.items():
            for msg_type, system_message in system_messages.items():
                try:
                    response = get_llm_response(llm, full_prompt, instruction_type=msg_type, 
                                                system_message=system_message, 
                                                temperature=temperatures[llm])
                    
                    # Split the response into answers for each question
                    answers = response.split('\n')
                    answers = [ans.strip() for ans in answers if ans.strip()][:len(questions)]
                    
                    # Assign responses and calculate similarities
                    start_idx = 0
                    for idx, row in group.iterrows():
                        num_questions = len(row['Questions'].split('|'))
                        row_answers = answers[start_idx:start_idx + num_questions]
                        row_answer_keys = answer_keys[start_idx:start_idx + num_questions]
                        
                        group.at[idx, f'Result_{llm}_{msg_type}'] = ' | '.join(row_answers)
                        
                        similarities = [calculate_similarity(ans.lower(), key.lower()) 
                                        for ans, key in zip(row_answers, row_answer_keys)]
                        group.at[idx, f'Similarity_{llm}_{msg_type}'] = sum(similarities) / len(similarities)
                        
                        start_idx += num_questions
                    
                except Exception as e:
                    print(f"Error querying {llm} with {msg_type} for link {link}: {str(e)}")
                    for idx in group.index:
                        group.at[idx, f'Result_{llm}_{msg_type}'] = f"Error: {str(e)}"
                        group.at[idx, f'Similarity_{llm}_{msg_type}'] = 0.0

    except Exception as e:
        print(f"Error processing link {link}: {str(e)}")
        for idx in group.index:
            for llm in llm_choices.keys():
                for msg_type in system_messages.keys():
                    group.at[idx, f'Result_{llm}_{msg_type}'] = f"Error: {str(e)}"
                    group.at[idx, f'Similarity_{llm}_{msg_type}'] = 0.0

def process_row(row, llm_choices, system_messages, temperatures):
    index = row.name
    term = row['Term']
    questions = row['Questions'].split('|')
    link = row['Link']
    answer_keys = row['AnswerKey'].split('|')

    try:
        # Scrape content from the link
        scraped_content = scrape_content(link)
        context = scraped_content['content']

        # Create the full prompt with multiple questions
        full_prompt = f"Term: {term}\nContext: {context}\n\nQuestions:\n"
        for i, question in enumerate(questions, 1):
            full_prompt += f"{i}. {question.strip()}\n"

        # Query each LLM with each system message
        for llm, model in llm_choices.items():
            for msg_type, system_message in system_messages.items():
                try:
                    response = get_llm_response(llm, full_prompt, instruction_type=msg_type, 
                                                system_message=system_message, 
                                                temperature=temperatures[llm])
                    
                    # Split the response into answers for each question
                    answers = response.split('\n')
                    answers = [ans.strip() for ans in answers if ans.strip()][:len(questions)]
                    
                    # Join answers with ' | ' separator
                    row[f'Result_{llm}_{msg_type}'] = ' | '.join(answers)
                    
                    # Calculate average similarity score
                    similarities = [calculate_similarity(ans.lower(), key.lower()) 
                                    for ans, key in zip(answers, answer_keys)]
                    row[f'Similarity_{llm}_{msg_type}'] = sum(similarities) / len(similarities)
                    
                except Exception as e:
                    print(f"Error querying {llm} with {msg_type} for row {index}: {str(e)}")
                    row[f'Result_{llm}_{msg_type}'] = f"Error: {str(e)}"
                    row[f'Similarity_{llm}_{msg_type}'] = 0.0

    except Exception as e:
        print(f"Error processing row {index}: {str(e)}")
        for llm in llm_choices.keys():
            for msg_type in system_messages.keys():
                row[f'Result_{llm}_{msg_type}'] = f"Error: {str(e)}"
                row[f'Similarity_{llm}_{msg_type}'] = 0.0

if __name__ == "__main__":
    # Load configuration
    with open('info.json', 'r') as f:
        config = json.load(f)

    # Input and output file paths
    input_file = 'input.xlsx'
    output_file = 'output.xlsx'

    # LLM choices (you can modify this based on your needs)
    llm_choices = {
        "GPT_4": config['models']['GPT_4'],
        "CLAUDE": config['models']['CLAUDE'],
        "GEMINI": config['models']['GEMINI']
    }

    # System messages to use
    system_messages = {
        "legal": config['instructions']['legal'],
        "data": config['instructions']['data']
    }

    # Temperatures (you can modify this based on your needs)
    temperatures = {
        "GPT_4": 0.7,
        "CLAUDE": 0.7,
        "GEMINI": 0.7
    }

    while True:
        user_input = input("Do you want to group up to 5 questions together per Link? (y/n): ").lower()
        if user_input in ['y', 'n']:
            group_by_link = user_input == 'y'
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    # Process the Excel file
    process_excel(input_file, output_file, llm_choices, system_messages, temperatures, group_by_link)