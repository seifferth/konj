#!/usr/bin/env python3

import sys
import os
import csv
import json
from random import shuffle, randint
from argparse import ArgumentParser

def pose_question(question: tuple, remaining="?") -> bool:
    q0, q1, s = question
    if "/" in q0:
        options = q0.split("/")
        i = randint(0,(len(options)-2))
        q0 = options[i]
        if "/" in s:
            s = s.split("/")[i]
    answer = input("[{}] {}".format(
        remaining,
        q0+" "+30*"_"+" ({})".format(q1)+(len(q1)+32)*"\b"
    ))
    if answer == "":
        print("Correct answer: \"{}\"".format(s))
        return False
    elif answer.lower() != s.lower():
        answer = input("Try again: ").strip()
        if answer.lower() != s.lower():
            print("Correct answer: \"{}\"".format(s))
        return False
    return True

def cli_quiz(questions: list, cache: dict=None):
    errors = list()
    def ask(q, points):
        """
        A wrapper around pose_question with side-effects.
        """
        r = len(questions) + len(errors) + 1
        correct = pose_question(q, remaining=r)
        if not correct:
            errors.append((q, int(points%2)))
        if cache != None:
            if q[1] not in cache.keys():
                cache[q[1]] = dict()
            if q[0] not in cache[q[1]].keys():
                cache[q[1]][q[0]] = 0
            if correct:
                cache[q[1]][q[0]] += points
            else:
                cache[q[1]][q[0]] = 0
    try:
        total = 1
        while len(questions) > 0:
            ask(questions.pop(), 3)
            if total%10 == 0:
                shuffle(errors)
                for _ in range(len(errors)):
                    ask(*errors.pop(0))
            total += 1
        shuffle(errors)
        while errors:
            ask(*errors.pop(0))
        return cache
    except (KeyboardInterrupt, EOFError):
        print()     # Ensure ending newline
        return cache

def load_questions(filenames: list):
    questions = list()
    def report_error(filename, line, column, existing, expected):
        print(
            "Error in input file \"{}\", line {}, field {}.".format(
                filename,
                line,
                column,
            ),
            "Expected {} backslash{} but found {}.".format(
                expected,
                "es" if expected > 1 else "",
                existing,
            ),
            sep="\n",
            file=sys.stderr
        )
    for filename in args.filename:
        with open(filename) as f:
            r = csv.reader(f, dialect="unix")
            header = next(r)
            for l, line in enumerate(r):
                for i in range(1, len(line)):
                    if line[i] == "":
                        continue
                    elif "/" in line[i]:    # Sanity-check special syntax
                        existing = len(line[i].split("/"))-1
                        expected = len(header[i].split("/"))-1
                        if not existing == expected:
                            report_error(filename, l+2, i, existing, expected)
                            exit(1)
                    questions.append((header[i],line[0],line[i]))
    return questions

cache_filename = "konj.cache"
def load_cache() -> dict:
    if os.path.isfile(cache_filename):
        with open(cache_filename) as f:
            cache = json.load(f)
    else:
        cache = dict()
    return cache
def save_cache(cache):
    with open(cache_filename, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
        f.write("\n")

def get_stats(questions, cache):
    stats = dict()
    for q0, q1, _ in questions:
        score = cache.get(q1, dict()).get(q0, 0)
        if score not in stats.keys():
            stats[score] = 0
        stats[score] += 1
    return stats

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("filename", nargs="+")
    parser.add_argument(
        "-n", "--number",
        help="maximum number of questions (default: 20; use -1 " + \
             "to disable this limit)",
        type=int, default=20,
    )
    parser.set_defaults(cache=True)
    parser.add_argument(
        "-C", "--no-cache",
        help="disable cache for this run",
        dest="use_cache", action="store_false",
    )
    parser.add_argument(
        "-v", "--verify",
        help="only run sanity checks against input files, " + \
             "do not start a quiz",
        action="store_true",
    )
    parser.add_argument(
        "-s", "--stats",
        help="print stats for a given file (or files) and exit",
        action="store_true",
    )
    args = parser.parse_args()

    questions = load_questions(args.filename)
    if args.verify:
        print("All files are correct.", file=sys.stderr)
        exit(0)
    if args.stats:
        stats = get_stats(questions, load_cache())
        scores = list(stats.keys())
        scores.sort()
        col1 = max(len("score"), len(str(max(stats.keys()))))
        col2 = max(len("items"), len(str(max(stats.values()))))
        frame = "  {:>"+str(col1)+"}  {:>"+str(col2)+"}"
        print(frame.format("score", "items"))
        print(frame.format(col1*"-", col2*"-"))
        for s in scores:
            print(frame.format(s, stats[s]))
        exit(0)

    cache = load_cache() if args.use_cache else None
    shuffle(questions)
    if args.number >= 0:
        questions = questions[:args.number]
    cache = cli_quiz(questions, cache=cache)
    if args.use_cache:
        save_cache(cache)
