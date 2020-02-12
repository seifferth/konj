#!/usr/bin/env python3

import sys
import os
import csv
import json
from random import shuffle, choice
from argparse import ArgumentParser

def pose_question(question: tuple, remaining="?") -> bool:
    q0, q1, s = question
    if "/" in q0:
        if "/" not in s:
            q0 = choice(q0.split("/"))
        else:
            solutions = s.split("/")
            shuffle(solutions)
            while solutions[-1] == "": solutions.pop()
            s0 = solutions[-1]
            i = s.split("/").index(s0)
            q0 = q0.split("/")[i]
            s = s0
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

def get_buckets(stats):
    """
    Figure out some way of dividing the input data into three
    buckets. Returns a list of tuples (min_score, max_score)
    that can be used to filter the data. The order of scores is
    (low, medium, high), which means that the order of difficulty
    is (high, medium, low).
    """
    lower_limit = min(stats.keys())
    upper_limit = max(stats.keys())
    total = sum(stats.values())
    remaining = total
    bucket_size = total/3
    # Try filling buckets, starting from lowest one
    i = lower_limit
    while remaining > 2.3*bucket_size:
        remaining -= stats.get(i, 0)
        i += 1
    b0 = (lower_limit, i)
    lower_limit = i+1;
    while remaining > 1.1*bucket_size:
        remaining -= stats.get(i, 0)
        i += 1
    b1 = (lower_limit, i)
    b2 = (i+1, upper_limit)
    return (b0, b1, b2)

def filter_questions(questions, min_score=None, max_score=None):
    if min_score != None:
        questions = list(filter(
            lambda x: cache.get(x[1], dict()).get(x[0], 0) >= min_score,
            questions,
        ))
    if max_score != None:
        questions = list(filter(
            lambda x: cache.get(x[1], dict()).get(x[0], 0) <= max_score,
            questions
        ))
    return questions

def print_table(table: list):
    """
    Print a 2-column table. All cells must be strings.
    """
    col1 = max(map(lambda row: len(row[0]), table))
    col2 = max(map(lambda row: len(row[1]), table))
    frame = "  {:>"+str(col1)+"}  {:>"+str(col2)+"}"
    left, right = table.pop(0)
    print(frame.format(left, right))
    print(frame.format(col1*"-", col2*"-"))
    for left, right in table:
        print(frame.format(left, right))


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
    parser.add_argument(
        "--buckets",
        help="print stats for buckets",
        action="store_true",
    )
    parser.add_argument(
        "-f", "--from",
        help="define the lowest score of items to be included",
        type=int,
    )
    parser.add_argument(
        "-t", "--to",
        help="define the highest score of items to be included",
        type=int,
    )
    parser.add_argument(
        "-d", "--difficulty",
        choices=["low", "medium", "high"],
        type=str,
    )
    args = parser.parse_args()

    questions = load_questions(args.filename)
    if args.verify:
        print("All files are correct.", file=sys.stderr)
        exit(0)

    cache = load_cache()
    questions = filter_questions(
        questions,
        min_score = args.__dict__["from"],
        max_score = args.__dict__["to"],
    )
    stats = get_stats(questions, cache)
    if args.difficulty or args.buckets:
        b0, b1, b2 = get_buckets(stats)
        q0 = filter_questions(questions, min_score=b0[0], max_score=b0[1])
        q1 = filter_questions(questions, min_score=b1[0], max_score=b1[1])
        q2 = filter_questions(questions, min_score=b2[0], max_score=b2[1])

    if args.stats:
        scores = list(stats.keys())
        scores.sort()
        table = list()
        table.append(["score", "items"])
        for s in scores:
            table.append([str(s), str(stats[s])])
        print_table(table)
        if args.buckets:
            print()
    if args.buckets:
        print_table([
            ["difficulty", "items"],
            ["high", str(len(q0))],
            ["medium", str(len(q1))],
            ["low", str(len(q2))],
        ])
    if args.buckets or args.stats:
        exit(0)

    if args.difficulty:
        shuffle(q0); shuffle(q1); shuffle(q2)
        if args.difficulty == "low":
            order = (q2, q1, q0)
        elif args.difficulty == "medium":
            order = (q1, q0, q2)
        elif args.difficulty == "high":
            order = (q0, q1, q2)
        questions = list()
        for bucket in order:
            questions.extend(bucket)
            questions.extend(bucket)
            questions.extend(bucket)
    else:
        shuffle(questions)
    if args.number >= 0:
        questions = questions[:args.number]
    cache = cli_quiz(questions, cache=cache)
    if args.use_cache:
        save_cache(cache)
