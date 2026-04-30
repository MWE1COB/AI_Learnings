import json
import random
import re
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from database import SKILL_LEVELS

# ── Fallback quiz bank (used when AI is not available) ───────────

FALLBACK_QUIZZES = {
    "C Programming": {
        1: [
            {"question": "What is the correct syntax to print 'Hello World' in C?",
             "options": ["printf('Hello World');", "print('Hello World');", "echo 'Hello World';", "console.log('Hello World');"],
             "answer": 0},
            {"question": "Which of the following is a valid C data type?",
             "options": ["string", "int", "boolean", "real"],
             "answer": 1},
            {"question": "What symbol is used to end a statement in C?",
             "options": [".", ":", ";", ","],
             "answer": 2},
            {"question": "Which header file is required for printf()?",
             "options": ["<stdlib.h>", "<math.h>", "<conio.h>", "<stdio.h>"],
             "answer": 3},
            {"question": "What is the correct way to declare an integer variable?",
             "options": ["integer x;", "int x;", "var x;", "x int;"],
             "answer": 1},
        ],
        2: [
            {"question": "What is the output of: printf(\"%d\", 5/2);?",
             "options": ["2.5", "2", "3", "Error"],
             "answer": 1},
            {"question": "Which loop is guaranteed to execute at least once?",
             "options": ["for", "while", "do-while", "foreach"],
             "answer": 2},
            {"question": "What does the 'break' statement do?",
             "options": ["Skips current iteration", "Exits the loop", "Pauses execution", "Ends the program"],
             "answer": 1},
            {"question": "What is a pointer in C?",
             "options": ["A data type", "A variable storing memory address", "A function", "An operator"],
             "answer": 1},
            {"question": "Which operator is used to access the value at a pointer address?",
             "options": ["&", "*", "->", "::"],
             "answer": 1},
        ],
        3: [
            {"question": "What is the difference between malloc() and calloc()?",
             "options": ["No difference", "calloc initializes memory to zero", "malloc is faster", "calloc is deprecated"],
             "answer": 1},
            {"question": "What is a segmentation fault?",
             "options": ["Syntax error", "Accessing invalid memory", "Stack overflow only", "Type mismatch"],
             "answer": 1},
            {"question": "What does 'static' keyword do for a local variable?",
             "options": ["Makes it global", "Retains value between function calls", "Makes it constant", "Allocates on heap"],
             "answer": 1},
            {"question": "Which is the correct way to dynamically allocate an array of 10 integers?",
             "options": ["int arr = malloc(10);", "int *arr = malloc(10 * sizeof(int));", "int arr[dynamic 10];", "int *arr = new int[10];"],
             "answer": 1},
            {"question": "What is a function pointer?",
             "options": ["Pointer returned by function", "Pointer to a function", "Function that returns pointer", "None of these"],
             "answer": 1},
        ],
        4: [
            {"question": "What is the purpose of volatile keyword in C?",
             "options": ["Speed optimization", "Prevents compiler optimization on the variable", "Makes variable constant", "Thread safety"],
             "answer": 1},
            {"question": "What is undefined behavior in C?",
             "options": ["Runtime error", "Compiler error", "Behavior not defined by the C standard", "Memory leak"],
             "answer": 2},
            {"question": "What is a union in C?",
             "options": ["Same as struct", "Members share same memory", "Collection of functions", "A type of array"],
             "answer": 1},
            {"question": "What does restrict qualifier do?",
             "options": ["Restricts access", "Hints pointer is the only reference to data", "Makes pointer const", "Limits scope"],
             "answer": 1},
            {"question": "What is the size of an empty struct in C?",
             "options": ["0", "1", "Undefined by standard", "4"],
             "answer": 2},
        ],
    },
    "Python": {
        1: [
            {"question": "Which keyword is used to define a function in Python?",
             "options": ["function", "func", "def", "define"],
             "answer": 2},
            {"question": "What is the output of print(type(5))?",
             "options": ["<class 'float'>", "<class 'int'>", "<class 'number'>", "<class 'str'>"],
             "answer": 1},
            {"question": "How do you create a list in Python?",
             "options": ["list = (1,2,3)", "list = [1,2,3]", "list = {1,2,3}", "list = <1,2,3>"],
             "answer": 1},
            {"question": "Which of the following is used for comments in Python?",
             "options": ["//", "/* */", "#", "--"],
             "answer": 2},
            {"question": "What is the correct file extension for Python files?",
             "options": [".python", ".pt", ".py", ".pn"],
             "answer": 2},
        ],
        2: [
            {"question": "What does 'len()' function do?",
             "options": ["Returns data type", "Returns length", "Returns last element", "Returns sorted list"],
             "answer": 1},
            {"question": "What is a dictionary in Python?",
             "options": ["Ordered list", "Key-value pairs", "Set of tuples", "Array of arrays"],
             "answer": 1},
            {"question": "What is list comprehension?",
             "options": ["A way to understand lists", "Concise way to create lists", "List sorting method", "List deletion method"],
             "answer": 1},
            {"question": "How do you handle exceptions in Python?",
             "options": ["if-else", "try-except", "catch-throw", "handle-error"],
             "answer": 1},
            {"question": "What does the 'self' parameter refer to in a class method?",
             "options": ["The class itself", "The instance of the class", "The parent class", "Global scope"],
             "answer": 1},
        ],
        3: [
            {"question": "What is a decorator in Python?",
             "options": ["A design pattern", "Function that modifies another function", "A class method", "A type of loop"],
             "answer": 1},
            {"question": "What is the difference between a list and a tuple?",
             "options": ["No difference", "Tuples are immutable", "Lists are immutable", "Tuples are faster to create"],
             "answer": 1},
            {"question": "What is a generator in Python?",
             "options": ["A random number creator", "Function that yields values lazily", "A class factory", "A file creator"],
             "answer": 1},
            {"question": "What does the GIL stand for?",
             "options": ["Global Integer Lock", "General Interpreter Lock", "Global Interpreter Lock", "General Integer Lock"],
             "answer": 2},
            {"question": "What is the purpose of __init__ method?",
             "options": ["Destructor", "Constructor/Initializer", "Class method", "Static method"],
             "answer": 1},
        ],
        4: [
            {"question": "What is a metaclass in Python?",
             "options": ["A class of a class", "A superclass", "An abstract class", "A mixin"],
             "answer": 0},
            {"question": "What is the descriptor protocol?",
             "options": ["File I/O protocol", "__get__, __set__, __delete__ methods", "Network protocol", "Iterator protocol"],
             "answer": 1},
            {"question": "What does __slots__ do?",
             "options": ["Creates time slots", "Restricts attribute creation, saves memory", "Enables multithreading", "Creates class slots"],
             "answer": 1},
            {"question": "What is monkey patching?",
             "options": ["A testing framework", "Dynamically modifying a class/module at runtime", "A design pattern", "Error handling technique"],
             "answer": 1},
            {"question": "What is the MRO in Python?",
             "options": ["Most Recent Object", "Method Resolution Order", "Multiple Return Objects", "Module Run Order"],
             "answer": 1},
        ],
    },
    "Java": {
        1: [
            {"question": "What is the entry point of a Java program?",
             "options": ["start()", "main()", "run()", "init()"],
             "answer": 1},
            {"question": "Which keyword is used to create an object in Java?",
             "options": ["create", "object", "new", "make"],
             "answer": 2},
            {"question": "Java is a _____ language.",
             "options": ["Procedural", "Functional", "Object-Oriented", "Scripting"],
             "answer": 2},
            {"question": "Which data type is used to store text in Java?",
             "options": ["char", "text", "String", "varchar"],
             "answer": 2},
            {"question": "What does JVM stand for?",
             "options": ["Java Variable Machine", "Java Virtual Machine", "Java Visual Machine", "Java Verified Machine"],
             "answer": 1},
        ],
        2: [
            {"question": "What is inheritance in Java?",
             "options": ["Creating new classes", "A class acquiring properties of another", "Method overloading", "Interface implementation"],
             "answer": 1},
            {"question": "What is the difference between == and .equals()?",
             "options": ["No difference", "== compares references, .equals() compares values", "== is faster", ".equals() is deprecated"],
             "answer": 1},
            {"question": "What is an interface in Java?",
             "options": ["A class", "A blueprint with abstract methods", "A variable type", "A package"],
             "answer": 1},
            {"question": "What is method overloading?",
             "options": ["Same name, different parameters", "Different name, same parameters", "Overriding a method", "Creating multiple classes"],
             "answer": 0},
            {"question": "What is the purpose of 'final' keyword?",
             "options": ["End the program", "Prevent modification/inheritance", "Define constants only", "Mark deprecated code"],
             "answer": 1},
        ],
        3: [
            {"question": "What is the difference between ArrayList and LinkedList?",
             "options": ["No difference", "ArrayList uses array, LinkedList uses nodes", "LinkedList is faster for all operations", "ArrayList is deprecated"],
             "answer": 1},
            {"question": "What is a lambda expression in Java?",
             "options": ["A class type", "Anonymous function implementation", "A loop construct", "An annotation"],
             "answer": 1},
            {"question": "What is the Stream API used for?",
             "options": ["File I/O", "Processing collections functionally", "Network streaming", "Thread management"],
             "answer": 1},
            {"question": "What is the purpose of 'synchronized' keyword?",
             "options": ["Speed up code", "Thread safety for shared resources", "Database sync", "File sync"],
             "answer": 1},
            {"question": "What is generics in Java?",
             "options": ["Generic classes only", "Type-safe parameterized types", "A design pattern", "Auto-boxing"],
             "answer": 1},
        ],
        4: [
            {"question": "What is the Java Memory Model?",
             "options": ["RAM management", "Specification for thread interaction with memory", "Garbage collection rules", "JVM architecture"],
             "answer": 1},
            {"question": "What is a ClassLoader?",
             "options": ["Compiles classes", "Loads class bytecode into JVM", "Creates objects", "Manages threads"],
             "answer": 1},
            {"question": "What is reflection in Java?",
             "options": ["Mirror pattern", "Inspecting/modifying classes at runtime", "Error handling", "Code generation"],
             "answer": 1},
            {"question": "What is the purpose of the 'volatile' keyword in Java?",
             "options": ["Makes variable constant", "Ensures visibility across threads", "Speeds up access", "Prevents garbage collection"],
             "answer": 1},
            {"question": "What is a PhantomReference used for?",
             "options": ["Strong referencing", "Pre-mortem cleanup actions", "Caching", "Thread pooling"],
             "answer": 1},
        ],
    },
}

# Add default quiz for topics not in fallback bank
DEFAULT_QUIZ = {
    1: [
        {"question": "What is the basic purpose of this technology?",
         "options": ["Data storage", "Building applications", "It depends on context", "All of the above"],
         "answer": 3},
        {"question": "Which is a fundamental concept in programming?",
         "options": ["Variables", "Recipes", "Blueprints", "Documents"],
         "answer": 0},
        {"question": "What does 'syntax' mean in programming?",
         "options": ["Program speed", "Rules of writing code", "Memory usage", "File size"],
         "answer": 1},
        {"question": "What is debugging?",
         "options": ["Writing code", "Finding and fixing errors", "Deleting code", "Compiling code"],
         "answer": 1},
        {"question": "What is an IDE?",
         "options": ["Internet Data Exchange", "Integrated Development Environment", "Internal Debug Engine", "Input Device Emulator"],
         "answer": 1},
    ],
}


# Timer allocation per question (in seconds) based on type and difficulty level
TIMER_CONFIG = {
    # level: {question_type: seconds}
    1: {"mcq": 20, "fill": 30},
    2: {"mcq": 25, "fill": 35},
    3: {"mcq": 30, "fill": 40},
    4: {"mcq": 35, "fill": 50},
}

PASS_PERCENTAGE = 80  # >=80% to pass


def get_quiz_timer(level, questions):
    """Calculate total quiz time based on question types and difficulty."""
    config = TIMER_CONFIG.get(level, TIMER_CONFIG[1])
    total = 0
    for q in questions:
        qtype = q.get("type", "mcq")
        total += config.get(qtype, 60)
    return total


def generate_quiz_with_ai(topic, level, num_questions=10):
    """Try to generate quiz using Google Gemini AI, fall back to local bank."""
    level_name = SKILL_LEVELS.get(level, "Beginner")

    if GENAI_AVAILABLE:
        try:
            return _generate_with_gemini(topic, level_name, num_questions)
        except Exception as e:
            print(f"AI generation failed: {e}, using fallback quiz bank.")

    return _get_fallback_quiz(topic, level, num_questions)


def _generate_with_gemini(topic, level_name, num_questions):
    """Generate mixed quiz questions using Google Gemini."""
    mcq_count = num_questions - 2  # 8 MCQ
    fill_count = 2

    prompt = f"""Generate exactly {num_questions} quiz questions for the topic "{topic}" at {level_name} difficulty level.
The quiz must contain a MIX of these 2 question types:
- {mcq_count} "mcq" (Choose the best answer): standard multiple choice with 4 options
- {fill_count} "fill" (Fill in the blank): a statement with a blank (______). User types the answer (no options given).

Return ONLY a valid JSON array with no additional text.

For "mcq" type:
- "type": "mcq"
- "question": the question text
- "options": array of exactly 4 answer options
- "answer": index (0-3) of the correct answer

For "fill" type:
- "type": "fill"
- "question": a statement with ______ for the blank
- "correct_text": the correct answer text (single word or short phrase)

Example format:
[
  {{"type": "mcq", "question": "What is X?", "options": ["A", "B", "C", "D"], "answer": 0}},
  {{"type": "fill", "question": "The ______ keyword is used to declare a variable.", "correct_text": "var"}}
]
"""
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    text = response.text.strip()

    # Extract JSON from response
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match:
        questions = json.loads(json_match.group())
    else:
        questions = json.loads(text)

    # Validate structure
    validated = []
    for q in questions[:num_questions]:
        qtype = q.get("type", "mcq")
        q["type"] = qtype

        if qtype == "mcq":
            if all(k in q for k in ("question", "options", "answer")):
                if isinstance(q["options"], list) and len(q["options"]) == 4:
                    if isinstance(q["answer"], int) and 0 <= q["answer"] <= 3:
                        validated.append(q)
        elif qtype == "fill":
            if all(k in q for k in ("question", "correct_text")):
                validated.append(q)

    if len(validated) < num_questions:
        raise ValueError(f"Only {len(validated)} valid questions generated")

    return validated


def configure_gemini(api_key):
    """Configure Google Gemini with the provided API key."""
    if GENAI_AVAILABLE:
        genai.configure(api_key=api_key)
        return True
    return False


def _get_fallback_quiz(topic, level, num_questions):
    """Get quiz from the local fallback bank with mixed question types."""
    topic_quizzes = FALLBACK_QUIZZES.get(topic, {})
    mcq_questions = list(topic_quizzes.get(level, DEFAULT_QUIZ.get(level, DEFAULT_QUIZ[1])))

    # Tag existing questions as MCQ
    tagged = []
    for q in mcq_questions:
        q_copy = dict(q)
        q_copy["type"] = "mcq"
        tagged.append(q_copy)

    # Generate fill-in-the-blank variants from MCQ (use last 2 so they don't overlap)
    fill_source = tagged[-2:] if len(tagged) >= 2 else tagged
    fill_questions = _generate_fill_from_mcq(fill_source, level)

    # Combine: fill + remaining MCQ to reach num_questions
    combined = fill_questions[:2]
    remaining = num_questions - len(combined)
    mcq_pool = tagged[:len(tagged) - len(fill_source)]
    if len(mcq_pool) < remaining:
        mcq_pool = tagged
    selected_mcq = mcq_pool[:remaining] if len(mcq_pool) >= remaining else mcq_pool * ((remaining // len(mcq_pool)) + 1)
    combined += selected_mcq[:remaining]

    random.shuffle(combined)
    return combined[:num_questions]


def _generate_fill_from_mcq(mcq_list, level):
    """Convert some MCQ questions into fill-in-the-blank format."""
    fill_questions = []
    for q in mcq_list[:3]:
        correct_idx = q["answer"]
        correct_ans = q["options"][correct_idx]
        fill_q = {
            "type": "fill",
            "question": q["question"].replace("?", "? (Fill in the blank)"),
            "correct_text": correct_ans,
        }
        fill_questions.append(fill_q)
    return fill_questions
