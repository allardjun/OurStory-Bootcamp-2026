# The same activity, typed instead of clicked

Everything you did by clicking buttons has a command behind it.
These are those commands.
You can run them in a Codespace (green **Code** button → **Codespaces** → **Create codespace on main**), which is a computer in your browser — nothing gets installed on your own machine.

## First: a Codespace is a different computer

This is the thing that confuses everybody, so it is worth getting straight before anything else.

A Codespace is a whole separate machine with **its own copy** of the story.
The copy on github.com is called **`origin`**.
The two do not talk to each other on their own.

- You edit `story.md` with the pencil on github.com → that change is now on `origin`. **Your Codespace still has the old version**, and `nano story.md` will show you the old text, until you run `git pull`.
- You edit `story.md` in the Codespace → that change is on the Codespace only. Nobody else can see it, not even github.com, until you `git add`, `git commit` and `git push`.

```bash
git pull                   # bring github.com's version down to here
git push                   # send this computer's version up to github.com
```

VS Code may show a small "↓1" near the branch name when github.com has something you do not.
That is only a notification — your files do not change until you actually `git pull`.

If you remember one thing: **nothing moves between the two until you ask it to.**

## Where am I, and what have I done?

```bash
git status                 # what have I changed but not saved yet?
git log --oneline          # the list of saves, newest first
./scripts/tree.sh          # the whole picture, including everyone else's copies
./scripts/blame.sh         # every line of the story, and who wrote it
```

`./scripts/tree.sh --watch` redraws the tree every ten seconds, which is worth leaving open during class.

If you have Graphviz installed (`brew install graphviz`), this draws the same tree as a picture instead:

```bash
./scripts/tree-image.sh    # writes tree.svg and tree.png
```

## Seeing everybody else

```bash
./scripts/classmates.sh --list   # who copied this repo, and who they copied it from
./scripts/classmates.sh          # pull all of their work into your copy
./scripts/tree.sh                # ...then draw the whole class as one picture
```

After running it, every classmate is available by name:

```bash
git branch -r                    # all their branches
git diff main alice/main         # what did alice change?
```

You did not need to sign in to anything for that.
A Codespace comes with the GitHub CLI already signed in, and a public repository's fork list can be read without credentials at all.

## Making a change

```bash
nano story.md              # edit the file (Ctrl-O to save, Ctrl-X to leave)

git add story.md           # choose what goes into this save
git commit -m "made the frog purple"   # save it, with a message
git push                   # send it up to GitHub
```

Those three commands are the whole loop, and you will type them for the rest of your career.

## Getting other people's work

```bash
git pull                   # bring down changes to my copy

git remote add upstream https://github.com/OWNER/REPO.git   # once only
git pull upstream main     # bring down changes from the original
```

Replace `OWNER/REPO` with the instructor's repository.
That last command is the typed version of the **Sync fork** button.

## When it says CONFLICT

```
CONFLICT (content): Merge conflict in story.md
Automatic merge failed; fix conflicts and then commit the result.
```

This is not an error, and nothing is lost.
Two people changed the same line and git wants you to decide.

```bash
nano story.md              # find the <<<<<<<, ======= and >>>>>>> markers
```

Keep the words you want, delete the words you do not, and delete all three marker lines.
Then:

```bash
git add story.md
git commit                 # no -m needed; it writes the message for you
git push
```

If you would rather start that merge over:

```bash
git merge --abort          # forget it ever happened, nothing is lost
```

## The two commands worth memorising

```bash
git status                 # when you do not know what is going on
git log --oneline          # when you do not know how you got here
```
