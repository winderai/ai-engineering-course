#! /bin/bash

# Update all branches to the latest main
git checkout main
git pull

for branch in $(git branch --list --no-color | sed 's/^\* //'); do
    echo "Updating $branch"
    git checkout $branch
    git pull
    git rebase origin/main
    git push -f
done
