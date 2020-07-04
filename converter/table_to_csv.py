import argparse
import csv
import errno
import os
from typing import Dict, Callable, Any, Optional, List

from lxml import etree


class XMLParser(object):
    """
    Incremental parsing of an XML file.
    Each element in the tag context is processed via a callable.
    A namespace map is automatically added to `callable_kwargs` if applicable.

    :param xml_file: XML file.
    :param python_callable: A function called for each element in the tag.
    :param callable_args: A list of positional arguments that will get unpacked in the callable.
    :param callable_kwargs: A dictionary of keyword arguments that will get unpacked in the callable.
    :param tag: Restrict elements to those elements that match the given tag, defaults to all elements.
        Namespaces must be declared in Clark's Notation: {URI}localname.
    :param dtd_validation: Validate the document against a DTD, defaults to False.
    :param schema: Validate the document against an XML schema (bytes version).
    """

    def __init__(self,
                 xml_file: str,
                 python_callable: Callable[[etree.Element, Any], None],
                 callable_args: Optional[List] = None,
                 callable_kwargs: Optional[Dict] = None,
                 tag: Optional[str] = None,
                 dtd_validation: bool = False,
                 schema: Optional[bytes] = None) -> None:

        if not callable(python_callable):
            raise TypeError('The `python_callable` parameter must be callable.')

        self.xml_file = xml_file
        self.python_callable = python_callable
        self.callable_args = callable_args or []
        self.callable_kwargs = callable_kwargs or {}
        self.tag = tag
        self.dtd_validation = dtd_validation
        self.schema = etree.XMLSchema(etree.XML(schema)) if schema else None

        if self.is_non_empty_file(self.xml_file):
            xml_tree = etree.iterparse(
                self.xml_file,
                tag=self.tag,
                dtd_validation=self.dtd_validation,
                events=('start-ns', 'end'),  # namespaces, element
                remove_blank_text=True,
                encoding='utf-8',
                schema=self.schema
            )
            self.fast_iteration(xml_tree)  # Iterate through parsed tag
        else:
            raise RuntimeError(f'{self.xml_file} is empty or non-existing.')

    def fast_iteration(self, xml_tree: etree.iterparse) -> None:
        """
        A method to loop through a XML context, calling `python_callable` each time, and then
        clean up unneeded references.

        :param xml_tree: Return value from the iterparse API, tuple(event, element).
        """
        namespaces = {}

        for event, element in xml_tree:
            if event == 'start-ns':  # For 'start-ns' element is a tuple (prefix, URI)
                prefix, url = element
                if not prefix:
                    prefix = 'ns'
                namespaces[prefix] = url  # Store namespace in a dictionary (prefix: URI)
            elif event == 'end':  # Process element
                if namespaces:
                    self.callable_kwargs.update({'namespaces': namespaces})
                self.python_callable(element, *self.callable_args, **self.callable_kwargs)
                element.clear()
                # Eliminate empty references from the root node to element
                for ancestor in element.xpath('ancestor-or-self::*'):
                    while ancestor.getprevious() is not None:
                        del ancestor.getparent()[0]

        del xml_tree

    @staticmethod
    def is_non_empty_file(file: str) -> bool:
        """
        Return True if file is not empty.
        """
        return os.path.isfile(file) and os.path.getsize(file) > 0

    @staticmethod
    def delete_file(file: str) -> None:
        """
        Delete file (which may not exist).
        Note: errno.ENOENT <=> no such file or directory.
        """
        try:
            os.remove(file)
            print(f'File deleted: {file}.')
        except OSError as os_error:
            if os_error.errno != errno.ENOENT:
                print(f'{str(os_error)}.')


def convert_to_csv(element: etree.Element, **kwargs) -> None:
    """
    Write/append row to CSV file.
    """
    row = []
    csv_file = kwargs.get('csv_file')
    namespaces = kwargs.get('namespaces')
    print(f'c1: {element.xpath("ns:c1/text()", namespaces=namespaces)}')

    with open(csv_file, mode='a', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for column in element:
            row.append(column.text)
        writer.writerow(row)


if __name__ == '__main__':
    schema_xml = None
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-t',
        '--tag',
        help="XML context",
        type=str)
    parser.add_argument(
        '-i',
        '--input',
        help='Path to XML file',
        type=str,
        required=True)
    parser.add_argument(
        '-o',
        '--output',
        help='Path to CSV file',
        type=str,
        required=True)
    parser.add_argument(
        '-s',
        '--schema',
        help='Path to XSD file',
        type=str)
    args = parser.parse_args()

    if XMLParser.is_non_empty_file(args.schema):
        with open(args.schema, mode='rb') as schema_file:
            schema_xml = schema_file.read()

    XMLParser.delete_file(args.output)

    print(f'Processing: {args.input}.')
    parser = XMLParser(
        xml_file=args.input,
        tag=args.tag,
        python_callable=convert_to_csv,
        callable_kwargs={'csv_file': args.output},
        schema=schema_xml
    )
    print('Done!')
