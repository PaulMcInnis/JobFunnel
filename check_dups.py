import fileinput
seen = set() # set for fast O(1) amortized lookup
for line in fileinput.FileInput('demo_job_search_results\demo_search.csv', inplace=1):
    if line in seen: continue # skip duplicate

    seen.add(line)
    print(f'Duplicate Files{line,}') # standard output is now redirected to the file