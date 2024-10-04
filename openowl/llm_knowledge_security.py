

# TODO: Instruct llm to follow vulnerability scoring methodologies such as 
# https://www.first.org/cvss/v4.0/specification-document, as used by the ossf: https://ossf.github.io/osv-schema/#severitytype-field

bug_classes = """

1. Memory Management Issues
   - Memory leaks: Failure to properly deallocate memory, leading to resource exhaustion
   - Use-after-free errors: Accessing memory after it has been freed
   - Double free errors: Attempting to free memory that has already been deallocated

2. Concurrency Problems
   - Race conditions: Unexpected behavior due to the timing or ordering of events
   - Deadlocks: Two or more threads are unable to proceed because each is waiting for the other
   - Thread safety issues: Incorrect sharing or synchronization of data between threads

3. Pointer Mishandling
   - Null pointer dereferences: Attempting to use a null pointer as if it pointed to a valid object
   - Dangling pointers: Using a pointer that references memory which has been freed

4. Error Handling Flaws
   - Unhandled exceptions: Failing to catch and properly handle exceptions
   - Improper error propagation: Incorrectly passing or managing error states

5. API Misuse
   - Incorrect function usage: Using API functions in ways not intended by the designers
   - Version incompatibilities: Issues arising from differences between API versions

6. Performance Issues
   - Algorithmic inefficiencies: Using suboptimal algorithms for specific tasks
   - Resource exhaustion: Consuming excessive system resources (CPU, memory, disk space)

7. Input Validation and Injection
   - SQL injection: Inserting malicious SQL code into application queries
   - Command injection: Executing arbitrary commands on the host operating system
   - Cross-site scripting (XSS): Injecting malicious scripts into web applications
   - LDAP injection: Manipulating LDAP queries to bypass authentication or access unauthorized information

8. Authentication and Session Flaws
   - Broken authentication: Flaws in the authentication process that allow attackers to impersonate users
   - Session management issues: Improper handling of session tokens leading to session hijacking or fixation

9. Access Control Weaknesses
   - Incorrect permission settings: Granting excessive or inappropriate access rights
   - Insecure direct object references: Allowing unauthorized access to resources through manipulation of object references

10. Cryptographic Weaknesses
    - Insecure data storage: Improper protection of sensitive data
    - Use of weak or obsolete algorithms: Relying on cryptographic methods that can be easily broken

11. Misconfigurations
    - Default or weak credentials: Using easily guessable or default passwords
    - Incorrect security settings: Improper setup of security features or controls

12. Data Exposure Risks
    - Unintended information disclosure: Exposing confidential data
    - Insufficient logging and monitoring: Lack of proper auditing and alerting mechanisms

13. Cross-Site Request Forgery (CSRF)
    - Forcing users to perform unwanted actions on a web application they're authenticated to

14. Buffer-Related Vulnerabilities
    - Buffer overflows: Writing data beyond the end of allocated memory, potentially allowing code execution
    - Buffer underflows: Writing data before the beginning of allocated memory, potentially allowing code execution

15. Hazardous Input Handling
    - Improper sanitization: Failure to properly clean or validate input data, leading to various attacks
    - Type confusion: Treating data of one type as if it were a different type, potentially leading to memory corruption or code execution
"""




# Taken from: https://www.browserstack.com/guide/types-of-software-bugs
# "Different Types of Software Bugs: Here are the most common types of software bugs or defects encountered in software testing so that developers and testers can deal with them better."
"""

1. Functional Bugs
Functional bugs are associated with the functionality of a specific software component.
In simple terms, any component in an app or website that doesn’t function as intended is a functional bug.
Such bugs are often detected when testers conduct comprehensive functional testing for their apps or websites in real user conditions. Teams need to ensure that all the functional bugs are resolved in the early stages so as to avoid delivering bad user experiences in the production environment.
For example, a Login button doesn’t allow users to login, an Add to cart button that doesn’t update the cart, a search box not responding to a user’s query, etc.

2. Logical Bugs
A logical bug disrupts the intended workflow of software and causes it to behave incorrectly. These bugs can result in unexpected software behavior and even sudden crashes. Logical bugs primarily take place due to poorly written code or misinterpretation of business logic.
For example of logical bugs include:
Assigning a value to the wrong variable.
Dividing two numbers instead of adding them together resulting in unexpected output

3. Workflow Bugs
Workflow bugs are associated with the user journey (navigation) of a software application.
Let’s consider an example of a website where a user needs to fill up a form regarding their medical history. After filling the form, the user has three options to choose from:
Save
Save and Exit
Previous Page
From the available options, if the user clicks on “Save and Exit,” the user intends to save the entered information and then exit. However, if clicking on the Save and Exit button leads to an exit from the form without saving the information, it leads to a workflow bug.
BrowserStack Test Observability Banner

4. Unit Level Bugs
Unit level bugs are very common, and they are typically easier to fix. Once the initial modules of software components are developed, developers perform unit testing to ensure that the small batches of code are functioning as expected. Here’s where developers encounter various bugs that get overlooked in the coding stages. Unit level bugs are easier to isolate as developers deal with a comparatively small amount of code. Moreover, replicating these bugs takes less time, so developers can track the exact bug and fix it in no time.
For example, if a developer creates a single page form, a unit test will verify whether all the input fields are accepting appropriate inputs and validate buttons for functionality. In case a field doesn’t accept the appropriate characters or numbers, developers encounter a unit-level bug.
Also Read: Popular Unit Testing Frameworks in Selenium

5. System-Level Integration Bugs
System-level integration bugs primarily pop up when two or more units of code written by different developers fail to interact with each other. These bugs primarily occur due to inconsistencies or incompatibility between two or more components. Such bugs are difficult to track and fix as developers need to examine a larger chunk of code. They are also time-consuming to replicate. Memory overflow issues and inappropriate interfacing between the application UI and the database are common examples of system-level integration bugs.
For example: An online booking system integrates with multiple third-party service providers (e.g., airlines, hotels). If one of the service providers experiences high latency or timeouts, the entire booking process may fail, resulting in incomplete bookings or incorrect availability information.

6. Out of Bound Bugs
Out of Bound Bugs show up when the system user interacts with the UI in an unintended manner. These bugs occur when an end-user enters a value or a parameter outside the limits of unintended use.
For example, entering a significantly larger or a smaller number or entering an input value of an undefined data type. These bugs often pop up in form validations during functional testing of web or mobile apps.
Must Read: A Detailed Guide on Bug Tracking

7. Security Bugs
Security is a major concern for software development. Security Bugs are a major risk for users and should be taken very seriously and resolved. Due to their high severity and vulnerable nature, security bugs are considered among the most sensitive bugs of all types and should be handled with criticality and urgency.
These bugs might not hinder the operation but can compromise the whole system. These should be checked thoroughly at regular intervals.
A common example is SQL injection, where an attacker can manipulate a database query to gain unauthorized access.

8. Performance Bugs
Performance bugs occur when a software application fails to meet the expected performance benchmarks, such as load times, response times, or throughput. These bugs can significantly degrade the user experience, especially in high-traffic or resource-intensive environments.
For example: An e-commerce website experiences a performance bug where the page load time exceeds 5 seconds during peak traffic hours, causing frustration for users and leading to a high abandonment rate.

9. Compatibility Bugs
Compatibility bugs arise when a software application does not function correctly across different environments, devices, or platforms. These bugs can lead to inconsistent user experiences and reduced accessibility.
For example: A mobile app works perfectly on Android devices but crashes or displays incorrectly on certain iOS devices, leading to a compatibility bug that impacts a significant portion of the user base.

10. Usability Bugs
Usability bugs affect the overall user experience, making it difficult or confusing for users to interact with the software. These bugs do not necessarily prevent functionality but can lead to poor user satisfaction and increased user error rates.
For example: A web application has a complex navigation structure that makes it difficult for users to find essential features, leading to a usability bug that frustrates users and reduces engagement.

11. Concurrency Bugs
Concurrency bugs occur in software systems that involve parallel processing or multi-threading. These bugs arise when multiple threads or processes interact in unintended ways, leading to unpredictable behavior, data corruption, or system crashes.
For example: A banking application experiences a concurrency bug where two users attempt to transfer funds simultaneously, leading to incorrect account balances or duplicate transactions.


"""



