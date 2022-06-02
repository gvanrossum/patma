# An Introduction to Pattern Matching


This tutorial is a gentle introduction to pattern matching in Python, as proposed by PEP 622.  The three lessons cover the essentials and core elements, but leave out some additional features.


## Lesson 1


Python has great support for sequences such as tuples and lists.  You might have used that already in assignment statements like `a, b = b, a` or when writing `return x, True` in a function to return two values all at once.  You can even combine both: if `f()` is your function that returns two values like the `return x, True` before, you can write `a, b = f()` to assign the value of `x` to `a` and `True` to `b`, say.

Sometimes you might not know the exact number of elements you want to unpack.  Even worse, `f()` might sometimes return five, sometimes only two elements.  How do you deal with that?  The star to the rescue!  It allows you to collect any number of elements into a new list and you can thus encode uncertainty about the _exact_ structure of the result you are expecting.



### A First Example

We take quite a simple function to start with: `indexOf()` checks whether a given substring occurs in a string `text`.  If so, it returns `True` together with the position of the first occurence of the substring in the text.  Otherwise it returns `False` and `-1` (which is quite an arbitrary choice and could be anything).
```python
def indexOf(substr, text):
    if substr in text:
        return True, text.index(substr)
    else:
        return False, -1
        
text = input("What are your favourite programming languages?")

(has_python, index) = indexOf("Python", text)

if has_python:
    print(f"Contains 'Python' at index {index}")
else:
    print("You are missing 'Python' in your list.")
```

Since the `-1` is a rather arbitrary choice for a text not found, we might want to get rid of that.  After all, it does not contain any useful information.  On the other hand, we might also want to know the last index at which the substring occurs in text.  However, this only makes sense if the substring occurs more than once.  This leads to a new `indexOf` function:
```python
def indexOf(substr, text):
    if substr in text:
        i = text.index(substr)
        j = text.rindex(substr)
        if i < j:
            return True, i, j
        else:
            return True, i
    else:
        return False,
```
Here is the trouble with this, though: how do we access the values returned by `indexOf()` for all the possible cases?  If we just write `has_python, index, last_index = indexOf(...)`, we might be met with an exception telling us that there are simply not enough values to unpack.

The star might come in very handy here: `has_python, *indices = indexOf(...)`, where `indices` is now a list containing zero, one or two elements.  The code for using the function then looks perhaps something like this:
```python
text = input("What are your favourite programming languages?")

(has_python, *indices) = indexOf("Python", text)

if has_python:
    if len(indices) > 1:
        (first, last) = indices
    else:
        first = last = indices[0]
    ...
else:
    print("You clearly forgot the best of them all!")
```

Another approach, more based on the "it's better to ask forgiveness than permission", would catch the exception when trying to unpack too long a sequence:
```python
text = input("What are your favourite programming languages?")
try:
    (has_python, first, last) = indexOf("Python", text)
except ValueError:
    try:
        (has_python, first) = indexOf("Python", text)
        last = first
    except ValueError:
        (has_python,) = indexOf("Python", text)
...
```



### Offering More Than One Possibility

Whether you prefer to check for the validity of your data first, or whether you try to catch an exception, both solutions above share the same characteristic: the code does not know the exact structure of the result they received, but need to unpack it in a meaningful way into some local variables, say.  In other words: unpacking with a fixed structure can fail, forcing us to try out more than one structure to find one that fits.  This is exactly the job for _pattern matching_!

Pattern matching lets you try out different unpacking scenarios for a given datum, until you find one that fits.  Each case clause offers one possibile structure for the _subject_, i.e. the result returned by the function `indexOf()`.
```python
text = input("What are your favourite programming languages?")
match indexOf("Python", text):
    case (has_python, first, last):
        print("Awesome!  Python seems important to you.")
        ...
    case (has_python, first):
        last = first
        print("Nice that you like Python!")
        ...
    case (has_python,):
        print("You clearly forgot the best of them all!")
```
As it turns out, such case clauses, which try to unpack a given subject, are quite versatile in their use.  Particularly functional programming makes heavy use of pattern matching.  Here is an example for a function that takes a sequence of values and pairs them up (e.g. `[2, 3, 5, 7] -> [(2, 3), (5, 7)]`).
```python
def build_pairs(seq):
    match seq:
        case [x, y, *rest]:   # recall that 'rest' can be empty!
            return [(x, y), *build_pairs(rest)]
        case [x]:
            return []
        case []:
            return []
```



### Function Overloading

The last example with the `build_pairs()` function already shows that pattern matching is not only useful when processing the result as returned from a function, but might be equally valuable when dealing with arguments passed into a function.

Python supports very flexible formal parameters in its function definitions, which cover a wide range of applications.  On the flipside, Python has no real support for overloaded functions, that is two functions that share a common name, but take differing numbers or kinds of arguments.  Yet, some built-in functions are clearly overloaded, such as `max`, for instance.  It either takes two numeric arguments and returns the higher of the two.  Or it takes a single argument, which has to be a non-empty sequence of numbers (actually, it must be an iterable object, but we will come back to that later).  Pattern matching allows us, as before, to deal with the different structure of parameters passed into the function.  In this example, we use the classic `*args` pattern to collect all arguments into a single tuple so that we can then differentiate different cases:
```python
def max(*args):
    match args:
        case (a, b):
            return a if a >= b else b
        case ([],):
            raise ValueError
        case ([result, *rest],):
            for x in rest:
                if x >= result: result = x
            return result
```
In a way, each case clause specifies a different implementation of the `max` function, each with its own list of parameters.  So, even though it is just a single function _syntactically_, it is as if we had defined three different functions with differing signatures (i.e. formal parameters).



### Matching on Dictionaries

In reality, we probably also have keyword arguments, which are not covered by pattern matching so far.  When capturing arbitrary keyword arguments, we end up with a dictionary rather than a simple tuple.  Luckily for us, pattern matching can also handle dictionaries, which makes it quite easy for us to implement a function that allows you to specify the coordinates of a rectangle in a couple of different ways:
```python
def create_rectangle(**kwargs):
    match kwargs:
        case { 'x': x, 'y': y, 'width': width, 'height': height }:
            pass
        case { 'left': x, 'top': y, 'right': right, 'bottom': bottom }:
            width = right - x
            height = bottom - y
        case { 'x1': x, 'y1': y, 'x2': right, 'y2': bottom }:
            width = right - x
            height = bottom - y
        case { 'x': cX, 'y': cY, 'radius': r }:
            x, y = cX - radius, cY - radius
            width = height = r * 2
    return Rect(x, y, width, height)
```
Once we are this far, there is naturally nothing stopping you from combining both possibilities:
```python
def create_rectangle(*args, **kwargs):
    match (args, kwargs):
        case ((x, y), { 'width': width, 'height': height }):
            pass
        case ((x, y), { 'right': right, 'bottom': bottom }):
            width = right - x
            height = bottom - y
        case ((), { 'x': x, 'y': y, 'width': width, 'height': height }):
            pass
        case ...:
            ...
    return Rect(x, y, width, height)
```
Note that patterns matching requires you to give specific key names.  You could not have a pattern like `{ key: value }`, say, but must give the key as a (string) literal.

The dictionary you are matching does not have to come from keyword-arguments, of course.  Here is an example of a function that extracts the country from a data set that is organised as a dictionary (like JSON).  Note that the dictionary `data` might contain many more elements, which are ignored by pattern matching: you only need to specify the keys you are really interested in.
```python
def get_country(data):
    match data:
        case { 'Country': country }:
            return country
        case { 'Capital': capital }:
            return find_country_from_capital(capital)
        case { 'Coordinates': (lat, long) }
            return find_country_from_gps(lat, long)
    return "?"
```



### Summary

Python's unpacking assignments as well as its parameter lists offer great support for sequences.  In contrast to Python's otherwise very dynamic nature, however, both of them require you to specify quite exactly what structure you expect the sequence to have, i.e. how many elements you anticipate.  Situations where you would like to allow for more than a single possible structure quickly require nested conditionals, repeated unpacking, or exception handling.

Pattern matching combines the idea of binding variables (be that assignment or argument passing) with the idea that the value might not fit the anticipated structure and this binding might thus fail.  It lets you offer an entire array of possible structures.  Python will then 'magically' find the first one that works and go with that.

Perhaps the main inspiration for pattern matching are parameters and arguments.  Pattern matching is what stands behind _function overloading_ in other programming languages: it lets you choose different implementations of a specific function, depending on the structure of the arguments (right now, _structure_ means the number of elements in a sequence, but as we progress, the notion of _structure_ will become more powerful, versatile and expressive).  Indeed, if you think of each case clause as something like a mini-function in its own right, you are right on track.  Patterns are primarily generalisations of formal arguments (parameters).

You will find pattern matching of sequences very frequently paired with recursion as in our `build_pairs` example above.  This is no accident: pattern matching favours a declarative style of programming that works very well with recursion and lets you succinctly reduce many problems to a base case and a divide-and-conquer paradigm.  You will see many more examples as we progress in this course.



### FAQ

**Why does `case (x, x):` not work?**
First off, patterns, such as the `(x, x)` here, are based on the notion of parameters, just as you already know them from functions.  They also borrow from sequence unpacking, of course, and try to get as close to the syntax you are already familiar with in everyday assignments.  Like parameters, however, there is no strict left-to-right rule in patterns: conceptually, Python tries to match a subject as a whole, not piecewise (although the implementation will naturally have to work step by step).

As you can nest patterns (as we did several times), you might end up with a pattern that looks like `([x, y], x, *t)`.  Which of these `x` should be bound first?  If you first unpack the (outer) tuple, you will bind values to the `x` on the right (and `t`) first, and then proceed with unpacking the list to bind the `x` on the left and `y`.  In a strict left-to-right manner, the order is exactly the other way round.

More importantly, however, `case (x, x):` might be (mis)understood as meaning a tuple with two equal elements, such as, e.g., `(2, 2)` or `('abc', 'abc')`, leading to bugs.

Retaining the rule inherited from parameters that each name must be unique thus avoids ambiguity about what the pattern really expresses and what values the individual variables might end up with.


**The dictionary pattern seems to ignore additional entries.**
Yes, the dictionary pattern (e.g. `{ 'width': width, 'height': height }`) only stipulates which elements are necessary and required.  In contrast to sequences with a clear ordering among all elements, dictionaries are more open, built for fast random-access and to be extended with additional key-value pairs whenever needed.  The `get_country` example shows a use case where the actual dictionary that is the subject of the pattern matching likely contains many additional entries, which are irrelevant here.

When dealing with keyword arguments, you might want to exclude additional entries.  You do this by binding the remaining entries to a new dictionary variable and then checking if it is empty:
```python
match kwargs:
    case { 'width': width, 'height': height, **rest }:
        if rest:
            raise TypeError("Unexpected keyword arguments.")
        ...
```

As we anticipate that in most scenarios these additional elements in a dictionary play no role at all, we decided to ignore them by default, rather than force to collect them into a `rest` variable (which is a rather expensive operation).


**Can I use attributes `foo.bar` or subscripts `a[i]` as targets?**
No, this is not possible, i.e. you cannot have a case clause of the form `case (self.x, self.y): ...` or `case (a[i+1], a[i-1]): ...`.  There are two reasons not to do this in patterns.

First, assignment targets such as attributes or subscript start by evaluating an expression.  In order to assign something to `foo.bar`, you look up `foo` first and then try to set the attribute `bar` on foo&mdash;which in turn might fail or be handled by `__setattr__`, involving arbitrary complex computations.  Subscripts are at least as complex and involved.  In reality, these assignments are more like "setters" in an OOP sense with calling a method than actual direct name bindings.  One effect of this is that patterns would have to be strictly ordered and would thus involve a complicated mix of evaluations, execution, and bindings.

Second, a pattern can fail to succeed at any point (which will get more complicated with "guards" in the next lesson).  While local name bindings can easily hold off until it is clear that a pattern actually succeeds, this is less obvious or simple for setters involving arbitrary objects.  A pattern trying to bind `self.x` and `self.y` could end up with only assigning a value to one of these attributes, effectively leaving the `self` object in a corrupt state&mdash;allthewhile the program continues without indication of such an issue.  Recall that pattern matching is explicitly about taking the possibility of a "matching failure" into account.


**Can I match/unpack iterables?**
Not the way you might expect from sequence unpacking: there is less magic happening behind the scenes.

In sequence unpacking, the source can be any iterable, which makes it extremely flexible and versatile.  With pattern matching, this gets more complicated, though, because pattern matching explicitly allows a specific pattern to "fail".  This means that patterns should avoid having any kind of side effect while attempt to match a subject.  For instance, as you will discover later on, you can easily specify patterns in such a way that a sequence with exactly two or three elements should be unpacked, whereas anything else should be left in its original form (perhaps for further processing).

You still have the possibility to explicitly turn an iterable into a sequence first, using something like `match tuple(my_iter): ...`.  But you need to explicitly mark that the iterator is read and turned into a sequence at this point.


**Why do you not introduce actual function overloading rather than pattern matching?**
With time, the formal parameters of Python functions have become quite versatile and complex in their ability to express default values and various flavours of positional as well as keyword arguments, not to mention annotations.  Adding the full power of patterns to the mix would quickly lead to overly complicated and way too complex structures.  Pattern matching as a separate statement, in contrast, has the advantage of introducing patterns in a narrowly specified context, so that its impact on the language as a whole is limited and controlled.


---


## Lesson 2


So far you have seen how pattern matching generalises the idea of unpacking a sequence by allowing you to offer a variety of possible "unpacking" structures and letting Python decide which one fits the actual data.  This behaviour is most commonly found as _function overloading_ in other programming languages.  Pattern matching in Python, however, lets you simlate both function overloading, as well as better deal with non-uniform results as returned by functions.  Recall that each case clause is like an anonymous function with its own parameters in the form of a pattern.

In this lesson, we will allow patterns to also add constraints on the contents of the sequence.



### Guards

A common exercise when learning a programming language is to write a function `is_palindrome()` that tells you whether a sequence or a string is a palindrome (recall that a palindrome is a sequence that is the same when read left-to-right as when read right-to-left, such as, e.g., "ANNA", "RADAR", "12321").  Using pattern matching and recursion, we can express this quite neatly, for instance like so:
```python
def is_palindrome(seq):
    match seq:
        case []:
            return True
        case [x]:
            return True
        case [x, *rest, y]:
            if x == y:
                return is_palindrome(rest)
    return False
```
In the last case you find that we impose an additional constraint on the sequence before accepting it as "successful": the first and last elements (i.e. `x` and `y`) must be equal.  This is not a constraint on the _structure_ of the data, but rather on its _contents_.  Accordingly, we cannot encode it directly as a pattern.  Yet, this last case does only make sense as a succesful match if `x` and `y` really are the same value.

Because such additional constraints are frequently needed to further specify an otherwise static pattern, you can combine the case clause directly with the if-statement and write everything onto one line:
```python
def is_palindrome(seq):
    match seq:
        case []:
            return True
        case [x]:
            return True
        case [x, *rest, y] if x == y:
            return is_palindrome(rest)
    return False
```
All this seems to do here is to save us a line.  But there is more to it: by combining the constraints with the pattern, Python will skip the entire pattern and _try the next one_ if the condition does not hold.  Observe:
```python
def is_ordered(seq):
    match seq:
        case []:
            return True, "ascending"
        case [x]:
            return True, "ascending"
        case [x, y] if x <= y:       # Third case
            return True, "ascending"
        case [x, y]:                 # Fourth case
            return True, "descending"
        case [x, y, z] if x <= y <= z:
            return True, "ascending"
        case [x, y, z] if x >= y >= z:
            return True, "descending"
        case [x, y, z]:
            return False,
    return None,
```
If you call this function with `is_ordered([4, 3])` you will get the answer `True, "descending"`.  The pattern of the third case matches the sequence with two elements successfully, but the guard nullifies that "success" because it does not fulfill the condition `4 <= 3`.  Because the pattern as a whole is not successful, Python will then go and try the next pattern, i.e. the fourth case, which succeeds, of course.

Had we written the condition as a separate if statement _inside_ the case clause's block, then the pattern would have succeeded and Python would not have tried any other pattern.



### Literal Values

Clearly, you can also use guards to compare elements of a sequence with contant values.  In this example, we trim a sequence of characters by removing any trailing spaces:
```python
def trim_seq(seq):
    match seq:
        case [first, *rest] if first == ' ':
            return trim_seq(rest)
        case [*rest, last] if last == ' ':
            return trim_seq(rest)
    return seq
```
Python lets you write this example more succinctly by embedding the literal values that an element must match directly into the patterns:
```python
def trim_seq(seq):
    match seq:
        case [' ', *rest]:
            return trim_seq(rest)
        case [*rest, ' ']:
            return trim_seq(rest)
    return seq
```
A note about strings: pattern matching does not handle strings as if they were sequences, but considers them to be atomic values.  This is why you need to explicitly turn your string into a sequence first, e.g., by calling `trim_seq(list(my_text))`.  Clearly distinguishing between strings and proper sequences lets you control better what your patterns should actually match.

Using literal values in patterns makes it particularly nice to handle non-uniform results from functions like `is_ordered()` above:
```python
match is_ordered(my_sequence):
    case (None,):
        print("Ordering unknown, sequence too long")
    case (False,):
        print("Clearly chaotic")
    case (True, order):
        print(f"In {order} order")
```



### Isolated Values

A function that returns only a single value seldomly does so by constructing a tuple containing that single value as we have done up to now.  Rather than `return False,` you would expect `return False` (without the trailing comma).  In fact, pattern matching can deal with such isolated values just as it can work with dictionaries.  Hence, you can actually write:
```python
def is_ordered(seq):
    match seq:
        case []:
            return True, "ascending"
        case [x]:
            return True, "ascending"
        case [x, y] if x <= y:
            return True, "ascending"
        case [x, y]:
            return True, "descending"
        case [x, y, z] if x <= y <= z:
            return True, "ascending"
        case [x, y, z] if x >= y >= z:
            return True, "descending"
        case [x, y, z]:
            return False
    return None

match is_ordered(my_sequence):
    case None:
        print("Ordering unknown, sequence too long")
    case False:
        print("Clearly chaotic")
    case (True, order):
        print(f"Ordered: {order}")
```

An example that comes up very frequently in the context of recursive functions and pattern matching is the `factorial()` function that computes `n! = 1*2*3*...*n`.  Using literals and an isolated variable rather than sequences, you might write it in Python like this:
```python
def factorial(arg):
    match arg:
        case 0:
            return 1
        case n:
            return n * factorial(n-1)
```
Note that the second case clause `case n:` actually matches any possible value and will thus always succeed.  Even if `arg` was a sequence, it would just bind `n` to the entire sequence.  In other words, `case n:` basically performs the assignment `n = arg`.



### Example: Event Handling

Pattern matching can be very handy when dealing with event in a GUI environment.  Depending on the kind of event that is reported, you receive a different set of parameters that are passed along with it, i.e. the event structure itself is polymorphic and does not have a single structure.  With the possibility of directly integrating string literals into the patterns, the handling of events becomes quite readable and aggregated in one central place.
```python
def handle_event(event):
    match event:
        case ("MouseDown", x, y, button):
            ...
        case ("MouseMoved", x, y):
            ...
        case ("MouseUp", x, y, button):
            ...
        case ("KeyPressed", char, shift):
            ...
        case ("KeyDown", code):
            ...
        case ("KeyUp", code):
            ...
```
A similar structure can be found when dealing with replies from a http server, which might take the form of:
```python
match reply:
    case (200, type, result):
        ...
    case (404, error_msg):
        ...
    case (418,):  # Teapots won't tell you much else
        ...
```



### Summary

Patterns express a _static_ structure, against which an object (the _subject_) is then matched.  However, this static structure sometimes does not suffice to fully capture the constraints imposed on the data.  Guards thus let you express additional _dynamic_ constraints, i.e. conditions that depend on the actual values and not only on the structure.

Moreover, you can even insert literal values directly into the patterns.  The subject then not only has to exhibit the required overall structure, but must be equal to the stipulated value.



### FAQ

**How do I use named constants in patterns?**
Given the possibility to use literal values, it seems logical to also use constant values.  It would be nice to write something like `case [SPACE, *rest]:` rather than `case [' ', *rest]:`.  However, this is not easily possible with pattern matching in Python: the compiler would simply regard `SPACE` as yet another name, just as if you had written `first` instead.  Of course, you can still use guards and write `case [first, *rest] if first == SPACE:`.

This is one of the places where it becomes obvious that patterns are not expressions, nor do they contain expressions as such.  Embedding literals is merely syntactic sugar for guards.  With named constants, the compiler simply cannot reliably decide whether any given name is a variable to be bound, or supposed to be a constant to be looked up and compared to the element at that position.

Of course, this could be solved with intricate rules or markers of some sort.  Some programming languages assume that all names starting with lowercase are variables/parameters to be bound, whereas names starting with an uppercase character denote constants.  Others use a prefix marker like `$` for constants.  Introducing a rule that determines the semantics of a name based on how it is written has no precedent in Python and would probably feel a bit alien to many Python developers.  Other rules or markers are just as problematic; however, if the need really arises, a marker might be introduced at some later point to pattern matching.


**How are subjects compared to literals?**
In general, the subject that is matched against a pattern is compared to a literal with the usual rules of equality `==`.  This means that `case 1:` will match not only the integer `1`, but also the floating point number `1.0` and even the boolean value `True`.  There is, however, an exception to this rule.  The three special values `True`, `False` and `None` only match themselves by identity, i.e. `is` semantics.  So, `case True:` will only match `True` and nothing else.  This means that there is an asymmetry in that `case 1:` matches `True`, but `case True:` does _not_ match `1` in turn.

Even today, it is customary to use `is` for comparison against the values `True`, `False` and `None` (i.e. you would write `if x is None` rather than `if x == None`).  Moreover, `case True:` matching numeric values as well would probably lead to some surprises, whereas the converse is less of an issue.


**Some of these match statements look awfully repetitive and inefficient.**
A central idea of pattern matching is the idea of _declarative prorgramming_.  This is to say that you just write down the patterns and structures as clearly and readable as possible, without worrying about how Python will then effectively find the correct pattern.  Pattern matching is seldomly compiled to a linear search through all the patterns.  The compiler will much rather create a very efficient decision tree, caching an previously established structures.  This is particularly true for guards.

With Python, such efficient compilation is a bit trickier and you might not yet observe the best possible performance.  We leave this rather for future work and keep in mind that JIT compilers like _PyPy_ and _Numba_ are already able to apply many optimisation techniques to Python code.  Any premature optimisation on pattern matching could thus lead to worse results in the long run.


**Pattern matching with literal values looks a lot like `switch`; what is the correspondence?**
Indeed, it is possible to use pattern matching for writing `switch`-statements as they are found in _C_, for instance.  However, it is important to keep in mind that this is more a happy accident than by design.  Conceptually, the two control structures are very different.

Switch developed out of a desire to quickly jump to a specific place in code based on an ordinal value.  In essence, it is a table translating numeric values or characters to a specific place in code and thus an action, i.e. the decision where to jump to is very simple and thus fast.  Pattern matching, on the other hand, is about trying to fit a data object to different possible structures.  Its control logic takes much rather the shape of a decision tree than of a table.  Pattern matching is not necessarily particularly fast, as its strength is in its versatility.

When you use pattern matching to write a switch-statement, it will be translated to a control structure with guards and eventually to a long `if`-`elif`-`else` chain.


---


## Lesson 3


Pattern matching is a versatile and powerful tool to deal with non-uniform sequential data.  It is based on the idea of trying to fit a given subject to different possible structure until one successfully described the actual structure of the subject in question.  Given the prevalence of sequential data, this turns out to offer a wide field of new opportunities.

Python, however, does not organise all its data strictly in sequential structures.  Most data is rather organised in objects with emphasis on named attributes rather than a fixed order.  It is only natural that we therefore want to extend pattern matching to such objects and their attributes and move beyond more sequences.



### Every Object a Sequence

There is simple solution for dealing with general objects and their data: turn the object into a sequence.  This is very similar to how you would serialise (pickle) an object to save it to disk or send it over a message channel to another interpreter, say.  In contrast to such serialisation, however, we do not necessarily need to capture all information stored in the object, but can concentrate on what is essential.

For each class that we want to use in pattern matching, we need to define a map that defines an order of attributes.  This map is specified through an attribute `__match_args__` on the class and is tuple of attribute names.  Let us demonstrate this with a class containing information about a person:
```python
class person:
    def __init__(self, name, gender, birth_date, address):
        self.name = name
        self.gender = gender
        self._birth_date = birth_date
        self.address = address
        self.town = address.town
        
    @property
    def age(self):
        return today().year - self._birth_date.year
        
    __match_args__ = ('name', 'gender', 'town', 'age')
```
Note that this `person` class does not expose all information stored, but rather exposes a few select fields, which might be most useful when working with persons in pattern matching.  This gives you a great deal of flexibility.

In pattern matching, you then put the class name right in front of the tuple, just as you would when defining a function:
```python
match p:
    case person(name, g, "London", age) if 20 <= age <= 29:
        print(f"{name} is a young person from London")
    case person(name, g, "London", age):
        print(f"{name} lives in London")
    case person(name, g, town, age) if 20 <= age <= 29:
        print(f"{name} is a young person")
```
By putting the class name in front of the tuple with the variables to bind, we actually mimic the syntax of function definitions.  It is almost as if we defned functions `def person(name, gender, town, age):` to deal with objects that are instances of `person`.  Again, pattern matching is highly related to parameters and each case clauses is almost a function definition of its own.  This similarity is thus deliberate and no accident.

What actually happens here is that Python will check whether the subject `p` is an instance of the class `person`.  If so, it will use `person.__match_args__` to get the names of the attributes whose values make up the sequence of values for pattern matching.



### Working with Attributes Directly

Objects can have a lot of possible attributes, and collecting them all in a sequence can become cumbersome and hard to remember.  It is therefore equally possible to specify the attributes that you are interested in directly by writing `attribute_name=pattern`.  The `person`-example above can thus also be written like this:
```python
match p:
    case person(name=n, town="London", age=a) if 20 <= a <= 29:
        print(f"{n} is a young person from London")
    case person(name=n, town="London"):
        print(f"{n} lives in London")
    case person(name=n, age=age) if 20 <= age <= 29:
        print(f"{n} is a young person")    
```




### Summary


### FAQ

