import json
from vllm import LLM, SamplingParams
import torch
import numpy as np  # Using numpy for easy mean calculation
from tqdm import tqdm

# test_type = "effective_uts"  # Change this to "buggy_uts_pair" if needed
# test_type = "misguided_uts"  # Change this to "buggy_uts_pair" if needed
# prompt_version = "buggy"  # Change this to "buggy" if needed
# generated_version = "fixed"  # Change this to "buggy" if needed
file_postfix = "unified_invoked"
# ut_generation_model = "Qwen-3-Coder-Plus"

# Using a variable for the model name
model_name = "openai/gpt-oss-120b"

# Initialize vLLM
print(f"Initializing vLLM with {model_name}...")
llm = LLM(
    model=model_name,
    # tensor_parallel_size=2,
    # quantization="awq",
    max_model_len=50000,
    gpu_memory_utilization=0.6
)
tokenizer = llm.get_tokenizer()
print("Model initialized.")

# Sampling parameters for scoring


# --- MODIFICATION STARTS HERE ---
# Lists to store scores for final calculations

# --- END OF MODIFICATION ---
ut_models = models = ['DeepSeek-R1', 'GPT-O4-MINI', 'Gemini-2-5-flash-thinking', 'Gemini-2-5-Pro',  'Grok-4', 'Qwen-3-Plus',
                      'Claude-4-Sonnet-extended-thinking', 'GPT-4-1', 'Claude-4-Sonnet', 'Gemini-2-5-flash', 'DeepSeek-V3',
                      'Grok-3', 'Qwen-3-Coder-Plus']

for ut_generation_model in ut_models:
    for generated_version in ['fixed', 'buggy']:
        if generated_version == 'buggy':
            test_type = 'misguided_uts'
        else:
            test_type = 'effective_uts'
        for prompt_version in ['fixed', 'buggy']:
            scoring_params = SamplingParams(
                max_tokens=1,
                prompt_logprobs=1
            )
            results_for_json = []
            all_normalized_scores = []
            all_prefix_averages = []
            qa_pairs_json_name = f"qa_pairs/{ut_generation_model}_comment_generation_full_{prompt_version}_{file_postfix}_prompt_{generated_version}_generated_{test_type}_pair.json"
            # Load the JSON file containing question-answer pairs
            with open(qa_pairs_json_name, 'r') as f:
                qa_pairs_to_score = json.load(f)
            print(f"Model: {ut_generation_model}, Generated Version: {generated_version}, Prompt Version: {prompt_version}, Test Type: {test_type}")
            pbar = tqdm(qa_pairs_to_score, total=len(qa_pairs_to_score), desc="Scoring QA Pairs")
            for item in pbar:
                prefix = item["prefix"]
                # Handle items with no responses
                if not item.get("responses"):
                    results_for_json.append({
                        "prefix": prefix,
                        "responses": [],
                        "responses_average": 0
                    })
                    print("Skipping item with no responses.")
                    continue

                # print(f"\n\n--- Scoring Prefix: {prefix!r} ---")

                prefix_formatted = tokenizer.apply_chat_template(
                    [{"role": "user", "content": prefix}],
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False
                )
                num_prefix_tokens = len(tokenizer.encode(prefix_formatted))
                # print(f"Prefix token count: {num_prefix_tokens}")

                scored_responses_data = []
                # --- MODIFICATION STARTS HERE ---
                current_prefix_scores = []  # Temp list for the current prefix's scores
                # --- END OF MODIFICATION ---

                for response in item["responses"]:
                    messages = [
                        {"role": "user", "content": prefix},
                        {"role": "assistant", "content": response}
                    ]
                    full_sequence = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        enable_thinking=False
                    )

                    outputs = llm.generate(full_sequence, scoring_params)

                    for output in outputs:
                        prompt_logprobs = output.prompt_logprobs
                        sequence_logprobs = prompt_logprobs[num_prefix_tokens:]
                        num_response_tokens = len(sequence_logprobs)
                        total_log_prob = 0.0
                        token_scores = []

                        if num_response_tokens > 0:
                            for logprob_dict in sequence_logprobs:
                                token_id = list(logprob_dict.keys())[0]
                                logprob = logprob_dict[token_id].logprob
                                total_log_prob += logprob
                                decoded_token = tokenizer.decode(token_id)
                                token_scores.append({"token": decoded_token, "logprob": round(logprob, 4)})
                            normalized_log_prob = total_log_prob / num_response_tokens
                        else:
                            total_log_prob = normalized_log_prob = 0.0

                        # --- MODIFICATION STARTS HERE ---
                        # Collect scores for averaging
                        all_normalized_scores.append(normalized_log_prob)
                        current_prefix_scores.append(normalized_log_prob)
                        # --- END OF MODIFICATION ---

                        # print(f"\nResponse: {response!r}")
                        # print(f"  -> Total Score:      {total_log_prob:.4f} ({num_response_tokens} tokens)")
                        # print(f"  -> Normalized Score: {normalized_log_prob:.4f} (Avg per token)")

                        scored_responses_data.append({
                            "response": response.strip(),
                            "token_scores": token_scores,
                            "token_count": num_response_tokens,
                            "total_score": round(total_log_prob, 4),
                            "normalized_score": round(normalized_log_prob, 4)
                        })

                # --- MODIFICATION STARTS HERE ---
                # Calculate the average score for the current prefix's responses
                responses_average = np.mean(current_prefix_scores) if current_prefix_scores else 0
                all_prefix_averages.append(responses_average)
                # print(f"\n  -> Average score for this prefix's responses: {responses_average:.4f}")

                # Add the prefix's average score to its dictionary
                results_for_json.append({
                    "prefix": prefix,
                    "responses": scored_responses_data,
                    "responses_average": round(responses_average, 4)
                })
                # --- END OF MODIFICATION ---

            # --- MODIFICATION STARTS HERE ---
            # Calculate the final overall and prefix averages
            overall_average = np.mean(all_normalized_scores) if all_normalized_scores else 0
            prefix_average = np.mean(all_prefix_averages) if all_prefix_averages else 0

            # Add the final summary dictionary to the results
            summary_data = {
                "overall_average": round(overall_average, 4),
                "prefix_average": round(prefix_average, 4)
            }
            results_for_json.append(summary_data)
            # --- END OF MODIFICATION ---

            # Write the final results to a JSON file
            output_filename = f"seq_score_record/{ut_generation_model}_{prompt_version}_prompt_{file_postfix}_{generated_version}_generated_{test_type}_{model_name.replace('/', '_')}_score.json"
            with open(output_filename, 'w') as f:
                json.dump(results_for_json, f, indent=4)

            print(f"\n\n✅ All scoring complete. Results have been written to {output_filename}")

            # --- MODIFICATION STARTS HERE ---
            # Print the final summary statistics
            print("\n--- Final Summary ---")
            print(f"Overall Average (per response): {overall_average:.4f}")
            print(f"Prefix Average (average of averages): {prefix_average:.4f}")
            print("---------------------")
            # open a file and append the final summary statistics
            filename = "final_summary_statistics.txt"
            with open(filename, 'a') as f:
                f.write(f"Model: {ut_generation_model}, Generated Version: {generated_version}, Prompt Version: {prompt_version}, Test Type: {test_type}\n")
                f.write(f"Overall Average (per response): {overall_average:.4f}\n")
                f.write(f"Prefix Average (average of averages): {prefix_average:.4f}\n")
                f.write("---------------------\n")
    # --- END OF MODIFICATION ---