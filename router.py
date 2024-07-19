import os
import json
from llms.llms import (llm_call_gpt, llm_call_claude, llm_call_gemini, llm_call_ollama, llm_call_groq)

# Load the configuration from info.json
with open('info.json', 'r') as f:
    config = json.load(f)

def get_llm_response(llm_choice, prompt, instruction_type='data', system_message=None, temperature=0.7):
    """
    Route the request to the appropriate LLM based on the choice and return the response.

    Args:
    llm_choice (str): The chosen LLM model.
    prompt (str): The input prompt for the LLM.
    instruction_type (str): The type of instructions to use (default is 'data').
    system_message (str): The system message to use. If None, it will be fetched from config.
    temperature (float): The temperature setting for the LLM (default is 0.7).

    Returns:
    str: The response from the chosen LLM.
    """
    # Get the specific model based on the choice
    model = config['models'].get(llm_choice)
    if not model:
        raise ValueError(f"Invalid LLM choice: {llm_choice}")

    # Get the appropriate instructions if not provided
    if system_message is None:
        system_message = config['instructions'].get(instruction_type)
    print(f"Using model: {model}")
    print(f"System message: {system_message}")

    # Route to the appropriate LLM call function
    if llm_choice in ['GPT_3.5', 'GPT_4']:
        return llm_call_gpt(model, prompt, system_message, temp=temperature)
    elif llm_choice in ['CLAUDE', 'CLAUDE_HAIKU']:
        return llm_call_claude(model, prompt, system_p=system_message, temp=temperature)
    elif llm_choice in ['GEMINI', 'GEMINI_FLASH']:
        return llm_call_gemini(model, prompt, system_message, temp=temperature)
    elif llm_choice == 'OLLAMA':
        # Note: Ollama doesn't support system messages in the same way, so we prepend it to the prompt
        full_prompt = f"{system_message}\n\n{prompt}"
        return llm_call_ollama(model, full_prompt, temp=temperature)
    elif llm_choice == 'GROQ':
        return llm_call_groq(model, prompt, system_message=system_message, temp=temperature)
    else:
        raise ValueError(f"Unsupported LLM choice: {llm_choice}")

if __name__ == "__main__":
    # Example usage
    llm_choice = "CLAUDE_HAIKU"
    prompt = "Analyze the legal implications of using AI in autonomous vehicles."
    instruction_type = "legal"

    try:
        response = get_llm_response(llm_choice, prompt, instruction_type)
        print(f"Response from {llm_choice}:")
        print(response)
    except Exception as e:
        print(f"An error occurred: {str(e)}")