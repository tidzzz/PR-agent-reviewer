import os
import sys
import json
from github import Github
from openai import OpenAI

def main():
    # 1. Initialize environment variables (injected by GitHub Actions)
    gh_token = os.environ.get("GITHUB_TOKEN")
    openai_key = os.environ.get("OPENAI_API_KEY")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    event_path = os.environ.get("GITHUB_EVENT_PATH")

    if not all([gh_token, openai_key, repo_name, event_path]):
        print("Error: Missing environment variables.")
        sys.exit(1)

    with open(event_path, 'r') as f:
        event_data = json.load(f)
        
    if "pull_request" not in event_data:
        print("Error: This action should be triggered by a pull_request event.")
        sys.exit(1)
        
    pr_number = event_data["pull_request"]["number"]

    # 2. Connect to the APIs
    gh = Github(gh_token)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    client = OpenAI(
        base_url="https://models.github.ai/inference",
        api_key=openai_key,
    )

    # 3. Retrieve the PR context
    pr_description = pr.body or "No description provided."
    
    # Retrieve the Git diff via GitHub's diff URL
    print("Retrieving the Git diff from the PR...")
    git_diff = ""
    for file in pr.get_files():
        git_diff += f"--- modified file : {file.filename} ---\n"
        if file.patch:
            git_diff += f"{file.patch}\n\n"
        else:
            git_diff += "binary or non textual modifications\n\n"
            
    if not git_diff.strip():
        git_diff = "any file changes could be retrieved from the PR."

    # 4. Read the instructions
    with open(".github/reviewer-instructions.md", "r", encoding="utf-8") as f:
        system_prompt = f.read()

    # 5. Build the prompt and call the LLM
    user_prompt = f"""
    --- PR DESCRIPTION ---
    {pr_description}
    
    --- GIT DIFF ---
    {git_diff}
    """
    
    print("Analyzing the PR with the LLM...")
    response = client.chat.completions.create(
        model="openai/gpt-4o", 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )
    
    llm_feedback = response.choices[0].message.content

    # 6. Take action on GitHub (comment + block)
    pr.create_issue_comment(llm_feedback)
    
    if "[VERDICT: FAIL]" in llm_feedback:
        print("❌ The PR failed the context/documentation audit.")
        sys.exit(1) # This is what marks the check as failed on GitHub.
    else:
        print("✅ PR approved by the agent.")
        sys.exit(0)

if __name__ == "__main__":
    main()