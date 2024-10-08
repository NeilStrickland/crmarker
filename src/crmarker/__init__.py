import json, sys, os, tempfile, contextlib, io, subprocess, base64, re
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

def do_marking(prefix, student_code, suffix = '', show_plot = False):
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
    failed = False
    try:
        with open('testcode.py', 'w') as fout:
            fout.write(test_program)
        outcome = subprocess.run(['python3', 'testcode.py'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  timeout=2, 
                                  universal_newlines=True,
                                  check=True)
    except subprocess.CalledProcessError as e:
        outcome = e
        output = f"Task failed with return code = {outcome.returncode}\n"
        failed = True
    except subprocess.TimeoutExpired as e:
        outcome = e
        output = "Task timed out\n"
    if outcome.stdout:
        output += outcome.stdout
    if outcome.stderr:
        output += '<span style="font-weight:bold; color:red">Error output:</span>' + "\n"
        output += tweak_line_numbers(outcome.stderr, prefix_length)

    mark = 1 if output.strip() == 'All good!' else 0
    html = ''
    if output:
        html += '<div>' + output + '</div><br/>'
    if show_plot and (not failed) and os.path.isfile('matplotliboutput.png'):
        data_uri = make_data_uri('matplotliboutput.png')
        html += """<img class="data-uri-example" title="Matplotlib plot" src="{}" alt="matplotliboutput.png">""".format(data_uri)

    result = {'prologuehtml': html, 'fraction': mark}
    print(json.dumps(result))    

## Subprocess functions
def matplotlib_setup():
    if 'MPLCONFIGDIR' not in os.environ or os.environ['MPLCONFIGDIR'].startswith('/home'):
        os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp()

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

def check_eval(GLOBALS, name, args, correct_val = None, 
               allow_output = False, allow_none = False, hide_args = False):
    """
    Try to evaluate the function name(args) in the GLOBALS dictionary.
    The function is evaluated in a context where stdout is redirected to a string,
    so that we can check if it prints anything.  It is also evaluated in a try block
    so that we can catch any exceptions that it raises.

    Parameters:
    GLOBALS: a dictionary of global variables
        This argument will always be the value returned by globals()
        in the calling function.   However, because of technicalities
        about scoping, we cannot just call globals() in this function.
    name: the name of the function to check
    args: a list of arguments to pass to the function
    correct_val: if not None, the function should return this value
        It is only appropriate to use this if a simple check using == 
        is adequate, and correct_val can conveniently be printed,
        and plausible return values can also be printed.
    allow_output: if True, the function is allowed to print output
    allow_none: if True, the function is allowed to return None
        Normally, if the function returns None, we flag it as a likely error.
    hide_args: This function returns various messages which usually 
        include the arguments passed to the function.  If hide_args is
        True, the messages will not include the arguments.  This is
        intended for cases where the string representation of the
        arguments would be too long or would not be helpful.

    Returns:
    (success, error_message, return_value)
    The error message is None if success is True.
    The return value is the value returned by the function.
    """
    func = GLOBALS[name]
    if hide_args:
        func_string = f"{name}(...)"
    else:
        args_string = ', '.join([str(arg) for arg in args])
        func_string = f"{name}({args_string})"
    try:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            val = func(*args)
    except Exception as e:
        msg = f"When evaluating <code>{func_string}</code>, your code raised an error: <code>{e}</code>"
        return False, msg, None
    if (not allow_output) and (out.getvalue().strip() != ''):
        msg = f"When evaluating <code>{func_string}</code>, your code printed something.  It should not do this."
        return False, msg, None
    if (val is None) and (not allow_none):
        msg = (f"When evaluating <code>{func_string}</code>, your function returned <code>None</code>. " + 
               "This probably means that you did not include a <code>return</code> statement.")
        return False, msg, None
    if correct_val is not None and val != correct_val:
        msg = (f"When evaluating <code>{func_string}</code>, your function should return <code>{correct_val}</code>, " + 
               f"but in fact it returns <code>{val}</code>.")
        return False, msg, val
    return True, None, val

def check_single_plot(output_file = 'matplotliboutput'):
    import matplotlib.pyplot
    nfigs = len(matplotlib.pyplot.get_fignums())
    if nfigs == 0:
        msg = """
Your code did not produce a plot that the marking system can check.
This could be because you did not produce a plot at all, or because
you called <code>plt.show()</code>, which makes the plot unavailable
to the marking system.
"""
        return False, msg, None, None
    else:
        fig = matplotlib.pyplot.gcf()
        ax = matplotlib.pyplot.gca()
        matplotlib.pyplot.savefig(output_file)
    if nfigs > 1:
        msg = """
Your code produced more than one plot.  This could mean that
(a) you did not just enter your function definition but added some 
extra code after the definition or (b) you called plt.figure() or 
plt.subplots() at an inappropriate time, resulting in the creation 
of a new plot.
"""
        return False, msg, fig, ax
    else:
        return True, None, fig, ax

def check_bare(fig, ax):
    """
    Check if the figure is 'bare' (i.e. has no axes, spines, ticks, or labels)
    Normally this would be achieved by calling ax.axis('off') but this 
    function also tries to check whether the same effect has been achieved
    by other means.
    """
    if not (ax.axison and fig.patch.get_visible()):
        return True
    if (ax.spines['top'].get_visible() or
        ax.spines['right'].get_visible() or
        ax.spines['left'].get_visible() or
        ax.spines['bottom'].get_visible()):
        return False
    if ((ax.get_xaxis().get_visible() and len(ax.get_xticks())) or
        (ax.get_yaxis().get_visible() and len(ax.get_xticks()))):
        return False
    return True
