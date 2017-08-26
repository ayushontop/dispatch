"""
Dispatch
Brian Yu
"""

import argparse
import csv
import getpass
import json
import smtplib
import sys
import termcolor
import traceback

from email.mime.text import MIMEText


def main():
    """
    Dispatch mass emails.
    """

    # Set up exception handler.
    sys.excepthook = excepthook

    # Parse command line arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="configuration file for dispatcher")
    parser.add_argument("data", help="csv data file with parameters")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show detailed output")
    args = vars(parser.parse_args())

    # Parse the configuration JSON file.
    config = parse_config(args["config"])

    # If the password is not specified, get the password.
    if "password" not in config:
        config["password"] = getpass.getpass()

    # Parse the data CSV file.
    headers, data = parse_data(args["data"])

    # Send one email for each row in the CSV file.
    for row in data:

        # Format the email parameters by substituting data from the CSV.
        params = {key: format_param(config[key], headers, row)
                  if key not in ["from", "password"] else config[key]
                  for key in config}

        # Send the email and print confirmation message.
        send_email(params)
        to = params.get("to", [])
        recipient = ", ".join(to) if isinstance(to, list) else to
        if args["verbose"]:
            print("Sent email to {} with parameters {}".format(
                  recipient, params))
        else:
            print("Sent email to {}".format(recipient))

    # Success!
    termcolor.cprint("Dispatch complete!", "green")


def excepthook(type, value, tb):
    """
    Global exception handler.
    """

    if type is Error and str(value):
        termcolor.cprint(str(value), "red")
    else:
        traceback.print_exception(type, value, tb)


def format_param(contents, headers, row):
    """
    Substitutes values (rows) based on keywords (headers) present in contents.
    """

    def format_param_string(contents, headers, row):
        """
        Performs substitution upon a string.
        """

        # Create a dictionary where keys should be substituted for values.
        subs = {key: row[headers[key]] for key in headers}
        try:
            return contents.format(**subs)
        except KeyError as e:
            raise Error("Missing parameter in data file: {}".format(e.args[0]))

    # If contents is a list, format elements. Otherwise, format the string.
    if isinstance(contents, list):
        return [format_param_string(item, headers, row) for item in contents]
    else:
        return format_param_string(contents, headers, row)


def parse_config(filename):
    """
    Parses a JSON configuration file.
    """

    # Open the file.
    try:
        f = open(filename, "r")
    except FileNotFoundError:
        raise Error("Configuration file {} does not exist.".format(filename))

    # Read the contents and parse as JSON.
    contents = f.read()
    f.close()
    try:
        data = json.loads(contents)
    except json.decoder.JSONDecodeError as e:
        raise Error("Invalid JSON in configuration file.\nError: {}".format(e))
    return data


def parse_data(filename):
    """
    Parses a CSV data file.
    """

    # Open the file.
    try:
        f = open(filename, "r")
    except FileNotFoundError:
        raise Error("Data file {} does not exist.".format(filename))

    # Read the data as a CSV.
    data = list(csv.reader(f, delimiter=","))

    # Use the first row to create a mapping of keywords to their column.
    headers, data = data[0], data[1:]
    headers = {headers[i].strip(): i for i in range(len(headers))}
    return headers, data


def send_email(params):
    """
    Sends an email.
    """

    # Check that all required fields are present.
    for field in ["from", "password", "subject", "body", "to"]:
        if not params.get(field):
            raise Error("Missing field {}.".format(field))

    # Set up SMTP server.
    server = smtplib.SMTP(
        params.get("server", "smtp.gmail.com"),
        int(params.get("port", 587))
    )
    server.ehlo()
    server.starttls()
    server.login(params.get("from", ""), params.get("password", ""))

    # Prepare message.
    msg = MIMEText(params.get("body"), "html")
    msg["Subject"] = params.get("subject", "")
    msg["From"] = params.get("username", "")
    for field in ["to", "cc", "bcc"]:
        addresses = params.get(field, [])
        if not isinstance(addresses, list):
            addresses = [addresses]
        msg[field.capitalize()] = ", ".join(addresses)

    # Send the message.
    server.send_message(msg)
    server.quit()


class Error(Exception):
    """
    Custom error class.
    """
    pass


if __name__ == "__main__":
    main()
