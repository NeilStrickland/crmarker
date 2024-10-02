import json
import sys
import contextlib
import io
import subprocess
from inspect import signature

## Main process functions
def ban_imports(student_func, die_on_error=True):
    """
    Check if the student's code contains the word "import".
    If it does, return False and print an error message.
    Otherwise, return True.
    """
    if "import" in student_func:
        output = 'The word "import" was found in your code.  Imports are not allowed in this question.'
        result = {'prologuehtml': output, 'fraction': 0}
        print(json.dumps(result))
        if die_on_error:
            sys.exit(0)
        return False
    return True

def make_data_uri(filename):
    """Given a png or jpeg image filename (which must end in .png or .jpg/.jpeg 
       respectively) return a data URI as a UTF-8 string.
    """
    with open(filename, 'br') as fin:
        contents = fin.read()
    contents_b64 = base64.b64encode(contents).decode('utf8')
    if filename.endswith('.png'):
        return "data:image/png;base64,{}".format(contents_b64)
    elif filename.endswith('.jpeg') or filename.endswith('.jpg'):
        return "data:image/jpeg;base64,{}".format(contents_b64)
    else:
        raise Exception("Unknown file type passed to make_data_uri")
    
def tweak_line_numbers(error, prefix_length):
    """Adjust the line numbers in the error message to account for extra lines"""
    new_error = ''
    for line in error.splitlines():
        match = re.match("(.*, line )([0-9]+)", line)
        if match:
            line = match.group(1) + str(int(match.group(2)) - prefix_length)
        new_error += line + '\n'
    return new_error

def do_marking(prefix, student_code, suffix = ''):
    """
    Mark a block of code submitted by a student.

    Parameters:
    prefix: a string containing code that should be inserted before 
            the student's code, typically containing import statements etc

    student_code: a string containing the student's code

    suffix: a string containing code that should be inserted after
            the student's code.  This will typically call 
    """
    output = ''
    test_program = prefix + "\n" + student_code + "\n" + suffix
    prefix_length = len(prefix.splitlines()) + 1

    try:
        with open('testcode.py', 'w') as fout:
            fout.write(test_program)
        output = subprocess.check_output(['python3', 'testcode.py'],
                                         stderr=subprocess.STDOUT, 
                                         universal_newlines=True)
    except subprocess.CalledProcessError as e:
        output = tweak_line_numbers(e.output, prefix_length)

    mark = 1 if output.strip() == 'All good!' else 0
    result = {'prologuehtml': output, 'fraction': mark}
    print(json.dumps(result))    

## Subprocess functions
def check_function(GLOBALS, name, args, require_docstring=True, allow_extra_args=False):
    """
    Check if the function name(args) is defined in the GLOBALS dictionary.

    Parameters:
    GLOBALS: a dictionary of global variables
    name: the name of the function to check
    args: a list of argument names
    require_docstring: a boolean.  If True, the function must have a non-empty docstring.
    allow_extra_args: a boolean.  If True, the function may have extra arguments.

    Returns:
    (success, error_message)
    The error message is None if success is True.
    """
    if not (name in GLOBALS):
        return False, f"You have not defined <code>{name}</code>."
    func = GLOBALS[name]
    if not (callable(func)):
        return False, f"You have not defined a function <code>{name}(...)</code>."
    args1 = list(signature(func).parameters)
    args2 = args1.copy()[:len(args)]
    full_name = f"{name}({', '.join(args)})"
    if allow_extra_args:
        if args2 != args:
            return False, f"You have not defined a function <code>{full_name}</code>."
    else:
        if args1 == args:
            pass
        elif args2 == args:
            return False, f"You have not defined a function <code>{full_name}</code>; your function <code>{name}()</code> has extra arguments."
        else:
            return False, f"You have not defined a function <code>{full_name}</code>."
    if require_docstring and (func.__doc__ is None or len(func.__doc__.strip()) == 0):
        return False, f"Your function <code>{full_name}</code> has no docstring."
    return True, None

def check_eval(GLOBALS, name, args, correct_val = None, allow_output = False):
    """
    Try to evaluate the function name(args) in the GLOBALS dictionary.
    The function is evaluated in a context where stdout is redirected to a string,
    so that we can check if it prints anything.  It is also evaluated in a try block
    so that we can catch any exceptions that it raises.

    Parameters:
    GLOBALS: a dictionary of global variables
    name: the name of the function to check
    args: a list of arguments to pass to the function
    correct_val: if not None, the function should return this value
    allow_output: if True, the function is allowed to print output

    Returns:
    (success, error_message, return_value)
    The error message is None if success is True.
    The return value is the value returned by the function.
    """
    func = GLOBALS[name]
    try:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            val = func(*args)
    except Exception as e:
        msg = f"When evaluating <code>{name}{tuple(args)}</code>, your code raised an error: <code>{e}</code>"
        return False, msg, None
    if (not allow_output) and (out.getvalue().strip() != ''):
        msg = f"When evaluating <code>{name}{tuple(args)}</code>, your code printed something.  It should not do this."
        return False, msg, None
    if val is None:
        msg = (f"When evaluating <code>{name}{tuple(args)}</code>, your function returned <code>None</code>. " + 
               "This probably means that you did not include a <code>return</code> statement.")
        return False, msg, None
    if correct_val is not None and val != correct_val:
        msg = (f"When evaluating <code>{name}{tuple(args)}</code>, your function should return <code>{correct_val}</code>, " + 
               f"but in fact it returns <code>{val}</code>.")
        return False, msg, val
    return True, None, val

