#!/bin/bash

# Set base directory
d4j_proj_base="d4j_proj_base"

# Create base directory if it doesn't exist
mkdir -p "$d4j_proj_base"

# List of projects
projects=$(defects4j pids)

# For each project
for project in $projects; do
    # Get list of bug IDs for the project
    bug_ids=$(defects4j bids -p $project)

    # For each bug ID
    for bug_id in $bug_ids; do
        # Construct Bug_id, e.g., Lang_1
        Bug_id="${project}_${bug_id}"

        # Create directory {Bug_id} under d4j_proj_base
        bug_dir="$d4j_proj_base/$Bug_id"
        mkdir -p "$bug_dir"

        # Checkout buggy version into {Bug_id}/buggy
        defects4j checkout -p $project -v ${bug_id}b -w "$bug_dir/buggy"

        # Checkout fixed version into {Bug_id}/fixed
        defects4j checkout -p $project -v ${bug_id}f -w "$bug_dir/fixed"
    done
done
