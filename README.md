# CRMarker

[Coderunner](https://coderunner.org.nz/) is a [Moodle](https://moodle.org/) question 
type which allows for automated marking of code samples submitted by students.  It 
supports code samples in a range of different languages, including Python.  This
package defines various useful functions for marking Python code.

Code in this package gets run in two different contexts.  There is a main 
process, which might perform some basic syntactic checks on the student's 
code, such as checking for disallowed import statements.  The main process
then adds a prefix and suffix to the student's code, spawns a new subprocess
to execute it, and collects anything that is sent to stdout during this 
execution.  The wrapper code is arranged so that messages printed by the
student code will not reach stdout, so the collected output will just consist
of messages printed by the wrapper code.  

The main process will typically import this package and call functions 
such as `do_marking()`.  The subprocess will typically also import this
package and call functions such as `check_function()` and `check_eval()`.