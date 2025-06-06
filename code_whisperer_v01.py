import streamlit as st
import json
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
import difflib
import asyncio
# from dotenv import load_dotenv
# import os
import re # Import regex module
import html # Import html module for unescaping
# Import the Google Generative AI client library
import google.generativeai as genai
# --- Configuration ---
# The API key will be automatically provided by the Canvas environment at runtime.
# It is crucial to leave this as an empty string and NOT to hardcode any API key here.
API_KEY = "AIzaSyDMF0VjgdWabTN-Cqy6X5Dj4ou9x8wjxH8" # This will be used to configure the genai client
# A dictionary mapping display names of languages to their Pygments lexer names.

SUPPORTED_LANGUAGES = {
    "Python": "python",
    "JavaScript": "javascript",
    "Java": "java",
    "C++": "cpp",
    "C#": "csharp",
    "Ruby": "ruby",
    "Go": "go",
    "SQL": "sql",
    "JSON": "json",
    "HTML": "html",
    "CSS": "css",
    "Text": "text"
}
# --- Helper Functions ---
def get_lexer_for_code(code: str, lang_name: str = None):
    """
    Determines the appropriate Pygments lexer for the given code.
    It first attempts to use the provided `lang_name` (if valid), then tries to guess
    the language from the code content. Falls back to a plain text lexer if all else fails.
    """
    if lang_name and lang_name in SUPPORTED_LANGUAGES:
        try:
            return get_lexer_by_name(SUPPORTED_LANGUAGES[lang_name])
        except Exception:
            pass
    try:
        return guess_lexer(code)
    except Exception:
        return get_lexer_by_name("text")
def highlight_code(code: str, lang_name: str = None) -> str:
    """
    Highlights the given code snippet using Pygments and returns it as HTML.
    """
    lexer = get_lexer_for_code(code, lang_name)
    formatter = HtmlFormatter(full=False, style="default")
    return highlight(code, lexer, formatter)
def generate_diff_html(old_code: str, new_code: str, lang_name: str = None) -> str:
    """
    Generates an HTML representation of the diff between two code snippets.
    """
    d = difflib.Differ()
    diff_lines = list(d.compare(old_code.splitlines(keepends=True), new_code.splitlines(keepends=True)))
    html_diff = []
    html_diff.append('<pre class="code-output-box">') # Use the same class for consistent styling
    for line in diff_lines:
        if line.startswith('+'):
            html_diff.append(f'<span style="color: #98c379;">{line}</span>')
        elif line.startswith('-'):
            html_diff.append(f'<span style="color: #e06c75;">{line}</span>')
        elif line.startswith('?'):
            pass
        else:
            html_diff.append(f'<span>{line}</span>')
    html_diff.append('</pre>')
    return "".join(html_diff)
async def call_gemini_api(prompt_text: str, generation_config: dict = None) -> str | None:
    """
    Makes an asynchronous call to the Gemini API to generate content using google-generative-ai.
    """
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        contents = [{"role": "user", "parts": [{"text": prompt_text}]}]
        response = await model.generate_content_async(contents, generation_config=generation_config)
        if response.candidates and response.candidates[0].content and \
           response.candidates[0].content.parts and response.candidates[0].content.parts[0].text:
            return response.candidates[0].content.parts[0].text
        else:
            st.error(f"Gemini API response did not contain expected text content. Raw response: {response.to_dict()}")
            return None
    except Exception as e:
        st.error(f"An error occurred calling Gemini API: {e}")
        return None
# --- Streamlit App Layout and Logic ---
st.set_page_config(layout="wide", page_title="Code Whisperer", page_icon="🧙🏻")
st.title("Code Whisperer 🧙🏻")
st.markdown("An AI-powered agent to explain, refactor, convert, and generate code.")
# --- Input Section ---
st.header("1. Input Your Code or Requirements")
col1, col2 = st.columns([3, 1])
with col1:
    with st.container(border=True): # Container for input code/requirements
        # Dynamically change label and placeholder based on selected action
        if st.session_state.get('action_radio', 'Explain Code') == "Vibe Code":
            code_input_label = "Describe your requirements and logic:"
            code_input_placeholder = "e.g., 'A Python function to calculate the factorial of a number recursively.'"
            code_input_height = 150 # Shorter height for requirements
        else:
            code_input_label = "Paste your code here:"
            code_input_placeholder = "Enter your code here (e.g., Python, JavaScript, Java, C++)..."
            code_input_height = 300 # Taller height for code
        code_input = st.text_area(
            code_input_label,
            height=code_input_height,
            placeholder=code_input_placeholder,
            key="code_input_area"
        )
with col2:
    source_lang_options = list(SUPPORTED_LANGUAGES.keys())
    selected_source_lang = st.selectbox(
        "Select Source Language (Optional, auto-detects if not chosen):",
        ["Auto-Detect"] + source_lang_options,
        key="source_lang_select"
    )
# --- Action Buttons ---
st.header("2. Choose an Action")
action = st.radio(
    "What would you like to do?",
    ("Explain Code", "Refactor Code", "Convert Code", "Vibe Code"),
    horizontal=True,
    key="action_radio"
)
# --- Conditional UI for Convert Code ---
if action == "Convert Code":
    st.subheader("Convert Code Options")
    target_lang_options = [lang for lang in source_lang_options if lang != selected_source_lang]
    selected_target_lang = st.selectbox(
        "Select Target Language:",
        target_lang_options,
        key="target_lang_select"
    )
# --- Conditional UI for Vibe Code (only target language selection) ---
if action == "Vibe Code":
    st.subheader("Vibe Code Options")
    vibe_target_lang = st.selectbox(
        "Preferred Output Language:",
        source_lang_options, # All supported languages can be target for Vibe Code
        key="vibe_target_lang_select"
    )
else:
    vibe_target_lang = None
# --- Process Button ---
if st.button("Process Code", use_container_width=True, key="process_button"):
    if not code_input.strip():
        if action == "Vibe Code":
            st.warning("Please describe your requirements for Vibe Code.")
        else:
            st.warning("Please enter some code to process.")
    else:
        actual_source_lang_name = selected_source_lang
        if selected_source_lang == "Auto-Detect" and action != "Vibe Code":
            try:
                guessed_lexer = guess_lexer(code_input)
                actual_source_lang_name = guessed_lexer.name
                st.info(f"Auto-detected language: **{actual_source_lang_name}**")
            except Exception:
                actual_source_lang_name = "Text"
                st.warning("Could not auto-detect language. Proceeding as plain text.")
        elif action == "Vibe Code":
            actual_source_lang_name = vibe_target_lang
        # Display the user's input code with syntax highlighting (only if not Vibe Code)
        if action != "Vibe Code":
            st.subheader("Your Input Code:")
            with st.container(border=True): # Container for input code display
                st.markdown(highlight_code(code_input, actual_source_lang_name), unsafe_allow_html=True)
        with st.spinner("Processing your request... This may take a moment."):
            response_text = None
            
            # Define a helper function to get language-specific formatting instruction
            def get_formatting_instruction(lang):
                if lang == "Python":
                    return " Ensure it strictly adheres to PEP 8 style guidelines."
                elif lang == "JavaScript":
                    return " Ensure it follows common JavaScript style guides (e.g., Airbnb, Google JavaScript Style Guide)."
                elif lang == "Java":
                    return " Ensure it follows common Java style guides (e.g., Google Java Format, Oracle Code Conventions)."
                elif lang == "C++":
                    return " Ensure it follows common C++ style guidelines (e.g., Google C++ Style Guide, LLVM Coding Standards)."
                elif lang == "C#":
                    return " Ensure it follows common C# coding conventions (e.g., Microsoft's C# Coding Conventions)."
                elif lang == "Ruby":
                    return " Ensure it follows common Ruby style guides (e.g., Ruby Style Guide)."
                elif lang == "Go":
                    return " Ensure it follows common Go style guidelines (e.g., Effective Go, Go's official formatting tools like gofmt)."
                elif lang == "SQL":
                    return " Ensure it follows common SQL formatting best practices (e.g., consistent casing, indentation, clear clause separation)."
                elif lang == "HTML":
                    return " Ensure it follows standard HTML formatting practices (e.g., proper indentation, semantic tags)."
                elif lang == "CSS":
                    return " Ensure it follows common CSS formatting practices (e.g., consistent indentation, property ordering)."
                elif lang == "JSON":
                    return " Ensure it is well-formatted JSON with proper indentation."
                else:
                    return " Ensure it follows idiomatic style and best practices for the language."
            if action == "Explain Code":
                formatting_instruction = get_formatting_instruction(actual_source_lang_name)
                prompt = f"""
                You are an expert code explainer. Explain the following {actual_source_lang_name} code line-by-line, and then provide a high-level summary of its purpose and functionality.
                Ensure your explanation is clear, concise, and easy to understand for developers.{formatting_instruction}
                Do not include the code itself in your response, only the explanation.
                Code:
                ```{SUPPORTED_LANGUAGES.get(actual_source_lang_name, "text")}
                {code_input}
                ```
                """
                response_text = asyncio.run(call_gemini_api(prompt))
                if response_text:
                    st.subheader("Code Explanation:")
                    st.markdown(response_text)
            elif action == "Refactor Code":
                formatting_instruction = get_formatting_instruction(actual_source_lang_name)
                prompt = f"""
                You are an expert code refactorer and optimizer. Analyze the following {actual_source_lang_name} code.
                Identify any "code smells" (e.g., redundancy, complexity, inefficiency, poor naming).
                Then, provide a refactored and optimized version of the code that improves readability, performance, and maintainability, without changing its external behavior.{formatting_instruction}
                The **ONLY** content inside the code block (```...```) must be pure, runnable code, free of any HTML tags, markdown formatting (like bold, italics, headers), or extra text.
                **DO NOT** include any text or explanation before the code block.
                After the code block, provide your explanation.
                Please format your response strictly as follows:
                ```refactored_{SUPPORTED_LANGUAGES.get(actual_source_lang_name, "text")}
                # [Refactored Code Here - PURE CODE ONLY]
                ```
                ---
                ### Explanation of Changes:
                # [Explanation of Changes Here]
                Code to refactor:
                ```{SUPPORTED_LANGUAGES.get(actual_source_lang_name, "text")}
                {code_input}
                ```
                """
                response_text = asyncio.run(call_gemini_api(prompt))
                if response_text:
                    # Use regex to robustly extract the code block content
                    code_match = re.search(rf"```refactored_{re.escape(SUPPORTED_LANGUAGES.get(actual_source_lang_name, 'text'))}\n(.*?)\n```", response_text, re.DOTALL)
                    
                    refactored_code = ""
                    explanation = ""
                    if code_match:
                        refactored_code = html.unescape(code_match.group(1).strip()) # Unescape HTML entities
                        # Extract explanation from the text after the code block
                        explanation_start_index = response_text.find("---", code_match.end())
                        if explanation_start_index != -1:
                            explanation_text_after_dash = response_text[explanation_start_index + 3:].strip()
                            explanation_match = re.search(r"### Explanation of Changes:\n(.*?)$", explanation_text_after_dash, re.DOTALL)
                            if explanation_match:
                                explanation = explanation_match.group(1).strip()
                            else:
                                # Fallback if "### Explanation of Changes:" is missing but "---" exists
                                explanation = explanation_text_after_dash.replace("### Explanation of Changes:", "").strip()
                        else:
                            explanation = "No explanation section found in the AI response."
                    else:
                        st.warning("Could not find the refactored code block in the AI response. Please check the AI's output format.")
                        # If code block not found, ensure variables are empty
                        refactored_code = ""
                        explanation = ""
                    if refactored_code:
                        st.subheader("Refactored Code:")
                        with st.container(border=True): # Container for refactored code display
                            st.markdown(highlight_code(refactored_code, actual_source_lang_name), unsafe_allow_html=True)
                        st.subheader("Code Diff (Original vs. Refactored):")
                        st.components.v1.html(generate_diff_html(code_input, refactored_code, SUPPORTED_LANGUAGES.get(actual_source_lang_name, "text")), height=400, scrolling=True)
                    if explanation:
                        st.subheader("Explanation of Changes:")
                        st.markdown(explanation)
                    # No else for warning here, as it's handled by the initial code_match check
            elif action == "Convert Code":
                if not selected_target_lang or selected_target_lang == selected_source_lang:
                    st.warning("Please select a valid target language different from the source language.")
                else:
                    formatting_instruction = get_formatting_instruction(selected_target_lang)
                    prompt = f"""
                    You are an expert code translator. Convert the following {actual_source_lang_name} code into {selected_target_lang} code.
                    Ensure the converted code is idiomatic to {selected_target_lang} and maintains the original functionality.{formatting_instruction}
                    The **ONLY** content inside the code block (```...```) must be pure, runnable code, free of any HTML tags, markdown formatting (like bold, italics, headers), or extra text.
                    **DO NOT** include any text or explanation before the code block.
                    After the code block, provide your explanation.
                    Please format your response strictly as follows:
                    ```converted_{SUPPORTED_LANGUAGES.get(selected_target_lang, "text")}
                    # [Converted Code Here - PURE CODE ONLY]
                    ```
                    ---
                    ### Conversion Notes:
                    # [Explanation of Conversion Here]
                    Code to convert:
                    ```{SUPPORTED_LANGUAGES.get(actual_source_lang_name, "text")}
                    {code_input}
                    ```
                    """
                    response_text = asyncio.run(call_gemini_api(prompt))
                    if response_text:
                        # Use regex to robustly extract the code block content
                        code_match = re.search(rf"```converted_{re.escape(SUPPORTED_LANGUAGES.get(selected_target_lang, 'text'))}\n(.*?)\n```", response_text, re.DOTALL)
                        
                        converted_code = ""
                        conversion_notes = ""
                        if code_match:
                            converted_code = html.unescape(code_match.group(1).strip()) # Unescape HTML entities
                            # Extract explanation from the text after the code block
                            explanation_start_index = response_text.find("---", code_match.end())
                            if explanation_start_index != -1:
                                explanation_text_after_dash = response_text[explanation_start_index + 3:].strip()
                                explanation_match = re.search(r"### Conversion Notes:\n(.*?)$", explanation_text_after_dash, re.DOTALL)
                                if explanation_match:
                                    conversion_notes = explanation_match.group(1).strip()
                                else:
                                    conversion_notes = explanation_text_after_dash.replace("### Conversion Notes:", "").strip()
                            else:
                                conversion_notes = "No conversion notes section found in the AI response."
                        else:
                            st.warning("Could not find the converted code block in the AI response. Please check the AI's output format.")
                            converted_code = ""
                            conversion_notes = ""
                        if converted_code:
                            st.subheader(f"Converted {selected_target_lang} Code:")
                            with st.container(border=True): # Container for converted code display
                                st.markdown(highlight_code(converted_code, selected_target_lang), unsafe_allow_html=True)
                        if conversion_notes:
                            st.subheader("Conversion Notes:")
                            st.markdown(conversion_notes)
                        # No else for warning here, as it's handled by the initial code_match check
            elif action == "Vibe Code":
                formatting_instruction = get_formatting_instruction(vibe_target_lang)
                prompt = f"""
                You are an expert code generator. Generate a {vibe_target_lang} code snippet based on the following requirements and logic:
                Requirements and Logic:
                {code_input}
                Ensure the generated code is functional, well-commented, and idiomatic to {vibe_target_lang}.{formatting_instruction}
                The **ONLY** content inside the code block (```...```) must be pure, runnable code, free of any HTML tags, markdown formatting (like bold, italics, headers), or extra text.
                **DO NOT** include any text or explanation before the code block.
                After the code block, provide your explanation.
                Please format your response strictly as follows:
                ```generated_{SUPPORTED_LANGUAGES.get(vibe_target_lang, "text")}
                # [Generated Code Here - PURE CODE ONLY]
                ```
                ---
                ### Explanation of Generated Code:
                # [Explanation Here]
                """
                response_text = asyncio.run(call_gemini_api(prompt))
                if response_text:
                    # Use regex to robustly extract the code block content
                    code_match = re.search(rf"```generated_{re.escape(SUPPORTED_LANGUAGES.get(vibe_target_lang, 'text'))}\n(.*?)\n```", response_text, re.DOTALL)
                    
                    generated_code = ""
                    explanation = ""
                    if code_match:
                        generated_code = html.unescape(code_match.group(1).strip()) # Unescape HTML entities
                        # Extract explanation from the text after the code block
                        explanation_start_index = response_text.find("---", code_match.end())
                        if explanation_start_index != -1:
                            explanation_text_after_dash = response_text[explanation_start_index + 3:].strip()
                            explanation_match = re.search(r"### Explanation of Generated Code:\n(.*?)$", explanation_text_after_dash, re.DOTALL)
                            if explanation_match:
                                explanation = explanation_match.group(1).strip()
                            else:
                                explanation = explanation_text_after_dash.replace("### Explanation of Generated Code:", "").strip()
                        else:
                            explanation = "No explanation section found in the AI response."
                    else:
                        st.warning("Could not find the generated code block in the AI response. Please check the AI's output format.")
                        generated_code = ""
                        explanation = ""
                    if generated_code:
                        st.subheader(f"Generated {vibe_target_lang} Code:")
                        with st.container(border=True): # Container for generated code display
                            st.markdown(highlight_code(generated_code, vibe_target_lang), unsafe_allow_html=True)
                    if explanation:
                        st.subheader("Explanation of Generated Code:")
                        st.markdown(explanation)
                    # No else for warning here, as it's handled by the initial code_match check
            if response_text is None:
                st.error("Failed to get a response from the AI. Please try again or refine your input.")
st.markdown("---")
st.markdown("Built with ❤️¸and Gemini API by Vivek")
# --- Custom CSS for Styling ---
st.markdown("""
<style>
    /* General styling for the Streamlit application */
    .stApp {
        background-color: #f0f2f6; /* Light grey background */
        color: #333; /* Dark grey text */
        font-family: 'Inter', sans-serif; /* Modern sans-serif font */
    }
    /* Styling for headers */
    h1, h2, h3 {
        color: #1a202c; /* Darker text for headers */
    }
    /* Styling for the primary button */
    .stButton>button {
        background-color: #f8f8f8; /* Off-white background */
        color: #333; /* Dark grey text */
        padding: 10px 24px; /* Padding for button size */
        border-radius: 8px; /* Rounded corners */
        border: 1px solid #ddd; /* Light border */
        cursor: pointer; /* Pointer cursor on hover */
        font-size: 16px; /* Font size */
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05); /* Subtle shadow */
        transition: all 0.3s ease; /* Smooth transitions for hover effects */
    }
    /* Hover effect for the primary button */
    .stButton>button:hover {
        background-color: #e6e6e6; /* Slightly darker background on hover */
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* Larger shadow on hover */
        transform: translateY(-1px); /* Slight lift effect */
    }
    /* Styling for text areas (code input) */
    .stTextArea textarea {
        border-radius: 8px; /* Rounded corners */
        border: 1px solid #ccc; /* Light grey border */
        padding: 10px; /* Inner padding */
        font-family: 'Fira Code', 'Cascadia Code', monospace; /* Monospace font for code */
        font-size: 14px; /* Font size for code */
    }
    /* Styling for select boxes (dropdowns) */
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 8px; /* Rounded corners */
        border: 1px solid #ccc; /* Light grey border */
    }
    /* Styling for radio button container */
    .stRadio > div {
        display: flex;
        justify-content: space-around;
        gap: 10px;
        padding: 10px;
        background-color: #e0e0e0;
        border-radius: 8px;
    }
    /* Styling for individual radio button labels */
    .stRadio label {
        padding: 8px 15px;
        border-radius: 5px;
        background-color: #f8f8f8;
        border: 1px solid #ddd;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    /* Hover effect for radio button labels */
    .stRadio label:hover {
        background-color: #e6e6e6;
    }
    /* Styling for the checked radio button */
    .stRadio input:checked + div {
        background-color: #4CAF50; /* Green background when checked */
        color: white;
        border-color: #4CAF50;
    }
    /* Custom styling for the code input/output boxes */
    .stContainer {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #ffffff; /* White background for the container */
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); /* Subtle shadow for depth */
    }
    /* Pygments default style overrides for a dark code theme */
    .highlight pre {
        background-color: #282c34 !important;
        color: #abb2bf !important;
        padding: 15px;
        border-radius: 8px;
        overflow-x: auto;
        font-family: 'Fira Code', 'Cascadia Code', monospace;
        font-size: 14px;
    }
    .highlight .k { color: #c678dd; }
    .highlight .kd { color: #c678dd; }
    .highlight .kn { color: #c678dd; }
    .highlight .kp { color: #c678dd; }
    .highlight .kr { color: #c678dd; }
    .highlight .kt { color: #e5c07b; }
    .highlight .n { color: #abb2bf; }
    .highlight .na { color: #e06c75; }
    .highlight .nb { color: #e5c07b; }
    .highlight .nc { color: #e5c07b; }
    .highlight .no { color: #d19a66; }
    .highlight .nd { color: #e06c75; }
    .highlight .ni { color: #e06c75; }
    .highlight .ne { color: #e06c75; }
    .highlight .nf { color: #61afef; }
    .highlight .nl { color: #e06c75; }
    .highlight .nn { color: #abb2bf; }
    .highlight .nx { color: #61afef; }
    .highlight .py { color: #e06c75; }
    .highlight .nt { color: #e06c75; }
    .highlight .nv { color: #d19a66; }
    .highlight .s { color: #98c379; }
    .highlight .sa { color: #98c379; }
    .highlight .sb { color: #98c379; }
    .highlight .sc { color: #98c379; }
    .highlight .dl { color: #98c379; }
    .highlight .sd { color: #98c379; }
    .highlight .s2 { color: #98c379; }
    .highlight .se { color: #e06c75; }
    .highlight .sh { color: #98c379; }
    .highlight .si { color: #98c379; }
    .highlight .sx { color: #98c379; }
    .highlight .sr { color: #98c379; }
    .highlight .s1 { color: #98c379; }
    .highlight .ss { color: #98c379; }
    .highlight .c { color: #5c6370; font-style: italic; }
    .highlight .cm { color: #5c6370; font-style: italic; }
    .highlight .cp { color: #5c6370; font-style: italic; }
    .highlight .c1 { color: #5c6370; font-style: italic; }
    .highlight .cs { color: #5c6370; font-style: italic; }
    .highlight .o { color: #56b6c2; }
    .highlight .ow { color: #56b6c2; }
    .highlight .p { color: #abb2bf; }
    .highlight .m { color: #d19a66; }
    .highlight .mf { color: #d19a66; }
    .highlight .mh { color: #d19a66; }
    .highlight .mi { color: #d19a66; }
    .highlight .mo { color: #d19a66; }
    .highlight .w { color: #abb2bf; }
    .highlight .err { color: #e06c75; background-color: #2d2d2d; }
    .highlight .gd { color: #e06c75; }
    .highlight .gi { color: #98c379; }
</style>
""", unsafe_allow_html=True)
