import yaml
import os
from dictdiffer import diff, patch, swap, revert
import sys
import argparse
import re
ignored_list = ["metadata.selfLink", "metadata.resourceVersion", "metadata.uid", "metadata.creationTimestamp",
                "metadata.managedFields", "status", "lifecycle", "args", "apiVersion", "terminationMessagePath",
                "terminationMessagePolicy", "scheme", "spec.template.spec.restartPolicy", "dnsPolicy", "schedulerName", "spec.clusterIP",
                "spec.sessionAffinity", "spec.template.spec.dnsPolicy"]


def yaml_printer(yaml_dict, indent_count):
    for elem in yaml_dict:
        if type(yaml_dict[elem]) is dict:
            if elem not in ignored_list:
                print(indent_count * '    ', elem, ":", sep='')
                yaml_printer(yaml_dict[elem], indent_count + 1)
        elif type(yaml_dict[elem]) is list:
            if elem not in ignored_list:
                print(indent_count * '    ', elem, ":", sep='')
                for list_elem in yaml_dict[elem]:
                    print((indent_count + 1) * '    ', "-", sep='')
                    yaml_printer(list_elem, indent_count + 2)
        else:
            if elem not in ignored_list:
                print(indent_count * '    ', elem, ": ", yaml_dict[elem], sep='')


def yaml_diff_printer_old(dry_dict, backup_dict, indent_count, value_name=None):
    if value_name is None:
        value_name = []
    for elem in dry_dict:
        if type(dry_dict[elem]) is dict:
            if elem not in ignored_list:
                if elem not in backup_dict.keys():
                    yaml_printer(dry_dict[elem], 0)
                else:
                    value_name.append(elem)
                    yaml_diff_printer_old(dry_dict[elem], backup_dict[elem], indent_count + 1, value_name)
        elif type(dry_dict[elem]) is list:
            if elem not in ignored_list:
                if elem not in backup_dict.keys():
                    print(f"Весь блок {elem}")
                else:
                    value_name.append(elem)
                    for list_elem in dry_dict[elem]:
                        value_name.append("-")
                        yaml_diff_printer_old(list_elem, backup_dict[elem], indent_count + 2, value_name)
        else:
            if elem not in ignored_list:
                if elem not in backup_dict.keys():
                    print(value_name, indent_count * '    ', elem, ": ", dry_dict[elem], sep='')


def dictionary_item_removed(keys):
    global_indent = len(str(keys))
    yaml_indent = 0
    print(f" {global_indent * 2 * '_'}")
    diff_type = "Исчез блок"
    tmp_left_indent = global_indent - len(diff_type) // 2
    tmp_right_indent = global_indent * 2 - (tmp_left_indent + len(diff_type))
    print(f"|{tmp_left_indent * ' '}{diff_type}{tmp_right_indent * ' '}|")
    print(f" {global_indent * 2 * '_'}")
    print(f"|Было{(global_indent - 5) * ' '}|Стало{(global_indent - 5) * ' '}|")
    print(f" {global_indent * 2 * '_'}")
    for elem in keys[:-2]:
        left_print = f"|{yaml_indent * '    '}{elem}:"
        print(left_print, end="")
        print(f"{(global_indent - len(left_print)) * ' '}|{global_indent * ' '}|")
        yaml_indent += 1
    left_print = f"|{yaml_indent * '    '}{keys[-2]}: {keys[-1]}"
    print(left_print, end="")
    print(f"{(global_indent - len(left_print)) * ' '}|{global_indent * ' '}|")
    yaml_indent += 1
    print(f"|{global_indent * 2 * '_'}|")


def dictionary_item_changed(keys, old_value, new_value):
    global_indent = len(keys) * 4 + max((max(len(str(old_value)),
                                                    len(str(new_value))),
                                                max(len(str(x)) for x in keys)))
    yaml_indent = 0
    print(f" {global_indent * 2 * '_'}")
    diff_type = "Изменилось значение"
    tmp_left_indent = global_indent - len(diff_type) // 2
    tmp_right_indent = global_indent * 2 - (tmp_left_indent + len(diff_type))
    print(f"|{tmp_left_indent * ' '}{diff_type}{tmp_right_indent * ' '}|")
    print(f" {global_indent * 2 * '_'}")
    print(f"|Было{(global_indent - 5) * ' '}|Стало{(global_indent - 5) * ' '}|")
    print(f" {global_indent * 2 * '_'}")
    for elem in keys:
        left_print = f"|{yaml_indent * '    '}{elem}:"
        print(left_print, end="")
        left_space_print = f"{(global_indent - len(left_print)) * ' '}|"
        right_print = f"{yaml_indent * '    '}{elem}:"
        right_space_print = f"{(global_indent - len(right_print)) * ' '}|"
        print(left_space_print, right_print, right_space_print, sep="")
        yaml_indent += 1
    left_print = f"|{yaml_indent * '    '}{old_value}"
    print(left_print, end="")
    left_space_print = f"{(global_indent - len(left_print)) * ' '}|"
    right_print = f"{yaml_indent * '    '}{new_value}"
    right_space_print = f"{(global_indent - len(right_print)) * ' '}|"
    print(left_space_print, right_print, right_space_print, sep="")
    print(f"|{global_indent * 2 * '_'}|")


def dictionary_item_added(keys):
    global_indent = len(str(keys))
    yaml_indent = 0
    print(f" {global_indent * 2 * '_'}")
    diff_type = "Добавился элемент"
    tmp_left_indent = global_indent - len(diff_type) // 2
    tmp_right_indent = global_indent * 2 - (tmp_left_indent + len(diff_type))
    print(f"|{tmp_left_indent * ' '}{diff_type}{tmp_right_indent * ' '}|")
    print(f" {global_indent * 2 * '_'}")
    print(f"|Было{(global_indent - 5) * ' '}|Стало{(global_indent - 5) * ' '}|")
    print(f" {global_indent * 2 * '_'}")
    for elem in keys[:-2]:
        left_space_print = f"|{global_indent * ' '}|"
        right_print = f"{yaml_indent * '    '}{elem}:"
        right_space_print = f"{(global_indent - len(right_print) - 1) * ' '}|"
        print(left_space_print, right_print, right_space_print, sep="")
        yaml_indent += 1
    left_space_print = f"|{global_indent * ' '}|"
    right_print = f"{yaml_indent * '    '}{keys[-2]}: {keys[-1]}"
    right_space_print = f"{(global_indent - len(right_print) - 1) * ' '}|"
    print(left_space_print, right_print, right_space_print, sep="")
    print(f"|{global_indent * 2 * '_'}|")


def yaml_diff_printer(diff):
    for diff_element in diff:
        if diff_element[0] == 'remove':
            changed_keys_list = []
            changed_key = []
            if isinstance(diff_element[1], str):
                first_part = diff_element[1].split(".")
                if isinstance(first_part, str):
                    changed_key.append(first_part)
                else:
                    changed_key.extend(first_part)
            second_part = diff_element[2]
            temp_changed_key = list(changed_key)
            for key in second_part:
                changed_key = list(temp_changed_key)
                changed_key.append(key[0])
                if isinstance(key[1], str):
                    changed_key.append(key[1])
                    changed_keys_list.append(changed_key)
                elif isinstance(key[1], dict):
                    temp_changed_key = list(changed_key)
                    for dict_element in key[1]:
                        changed_key = list(temp_changed_key)
                        changed_key.append(dict_element)
                        changed_key.append(key[1][dict_element])
                        changed_keys_list.append(changed_key)
            for aaaa_changed_key in changed_keys_list:
                dictionary_item_removed(aaaa_changed_key)
        elif diff_element[0] == 'change':
            changed_key = []
            if isinstance(diff_element[1], str):
                first_part = diff_element[1].split(".")
                if isinstance(first_part, str):
                    changed_key.append(first_part)
                else:
                    changed_key.extend(first_part)
            else:
                changed_key.extend(diff_element[1])
            second_part = diff_element[2]
            old_value = second_part[0]
            new_value = second_part[1]
            dictionary_item_changed(changed_key, old_value, new_value)
        elif diff_element[0] == 'add':
            changed_keys_list = []
            changed_key = []
            if isinstance(diff_element[1], str):
                first_part = diff_element[1].split(".")
                if isinstance(first_part, str):
                    changed_key.append(first_part)
                else:
                    changed_key.extend(first_part)
            second_part = diff_element[2]
            temp_changed_key = list(changed_key)
            for key in second_part:
                changed_key = list(temp_changed_key)
                changed_key.append(key[0])
                if isinstance(key[1], str):
                    changed_key.append(key[1])
                    changed_keys_list.append(changed_key)
                elif isinstance(key[1], dict):
                    temp_changed_key = list(changed_key)
                    for dict_element in key[1]:
                        changed_key = list(temp_changed_key)
                        changed_key.append(dict_element)
                        changed_key.append(key[1][dict_element])
                        changed_keys_list.append(changed_key)
            for aaaa_changed_key in changed_keys_list:
                dictionary_item_removed(aaaa_changed_key)


def yaml_diff_printer_old_2(ddiff):
    if 'type_changes' in ddiff.keys():
        for keys in ddiff['type_changes']:
            key = keys.replace('root[', '')
            key = key.replace('\'', '')
            key = key.replace(']', '')
            key = key.split('[')
            global_indent = len(key) * 4 + max((max(len(str(ddiff['type_changes'][keys]['old_value'])),
                                                    len(str(ddiff['type_changes'][keys]['new_value']))),
                                                max(len(x) for x in key)))
            yaml_indent = 0
            print(f" {global_indent * 2 * '_'}")
            diff_type = "Изменился тип данных"
            tmp_left_indent = global_indent - len(diff_type) // 2
            tmp_right_indent = global_indent * 2 - (tmp_left_indent + len(diff_type))
            print(f"|{tmp_left_indent * ' '}{diff_type}{tmp_right_indent * ' '}|")
            print(f" {global_indent * 2 * '_'}")
            print(f"|Было{(global_indent - 5) * ' '}|Стало{(global_indent - 5) * ' '}|")
            print(f" {global_indent * 2 * '_'}")
            for elem in key:
                left_print = f"|{yaml_indent * '    '}{elem}:"
                print(left_print, end="")
                left_space_print = f"{(global_indent - len(left_print)) * ' '}|"
                right_print = f"{yaml_indent * '    '}{elem}:"
                right_space_print = f"{(global_indent - len(right_print)) * ' '}|"
                print(left_space_print, right_print, right_space_print, sep="")
                yaml_indent += 1
            left_print = f"|{yaml_indent * '    '}{ddiff['type_changes'][keys]['old_value']}"
            print(left_print, end="")
            left_space_print = f"{(global_indent - len(left_print)) * ' '}|"
            right_print = f"{yaml_indent * '    '}{ddiff['type_changes'][keys]['new_value']}"
            right_space_print = f"{(global_indent - len(right_print)) * ' '}|"
            print(left_space_print, right_print, right_space_print, sep="")
            print(f"|{global_indent * 2 * '_'}|")

    if 'values_changed' in ddiff.keys():
        for keys in ddiff['values_changed']:
            # key = keys.replace('root', '').lstrip('[\'').rstrip('\']').split('\'][\'')
            key = keys.replace('root[', '')
            key = key.replace('\'', '')
            key = key.replace(']', '')
            key = key.split('[')
            global_indent = (len(key) + 2) * 4 + max(len(ddiff['values_changed'][keys]['old_value']),
                                                     len(ddiff['values_changed'][keys]['new_value']))
            yaml_indent = 0
            print(f" {global_indent * 2 * '_'}")
            diff_type = "Изменилось значение"
            tmp_left_indent = global_indent - len(diff_type) // 2
            tmp_right_indent = global_indent * 2 - (tmp_left_indent + len(diff_type))
            print(f"|{tmp_left_indent * ' '}{diff_type}{tmp_right_indent * ' '}|")
            print(f" {global_indent * 2 * '_'}")
            print(f"|Было{(global_indent - 5) * ' '}|Стало{(global_indent - 5) * ' '}|")
            print(f" {global_indent * 2 * '_'}")
            for elem in key:
                left_print = f"|{yaml_indent * '    '}{elem}:"
                print(left_print, end="")
                left_space_print = f"{(global_indent - len(left_print)) * ' '}|"
                right_print = f"{yaml_indent * '    '}{elem}:"
                right_space_print = f"{(global_indent - len(right_print)) * ' '}|"
                print(left_space_print, right_print, right_space_print, sep="")
                yaml_indent += 1
            left_print = f"|{yaml_indent * '    '}{ddiff['values_changed'][keys]['old_value']}"
            print(left_print, end="")
            left_space_print = f"{(global_indent - len(left_print)) * ' '}|"
            right_print = f"{yaml_indent * '    '}{ddiff['values_changed'][keys]['new_value']}"
            right_space_print = f"{(global_indent - len(right_print)) * ' '}|"
            print(left_space_print, right_print, right_space_print, sep="")
            print(f"|{global_indent * 2 * '_'}|")

    if 'dictionary_item_removed' in ddiff.keys():
        for keys in ddiff['dictionary_item_removed']:
            global_indent = len(keys)
            key = keys.replace('root[', '').replace('\'', '').replace(']', '').split('[')
            yaml_indent = 0
            print(f" {global_indent * 2 * '_'}")
            diff_type = "Исчез блок"
            tmp_left_indent = global_indent - len(diff_type) // 2
            tmp_right_indent = global_indent * 2 - (tmp_left_indent + len(diff_type))
            print(f"|{tmp_left_indent * ' '}{diff_type}{tmp_right_indent * ' '}|")
            print(f" {global_indent * 2 * '_'}")
            print(f"|Было{(global_indent - 5) * ' '}|Стало{(global_indent - 5) * ' '}|")
            print(f" {global_indent * 2 * '_'}")
            for elem in key:
                left_print = f"|{yaml_indent * '    '}{elem}:"
                print(left_print, end="")
                print(f"{(global_indent - len(left_print)) * ' '}|{global_indent * ' '}|")
                yaml_indent += 1
            print(f"|{global_indent * 2 * '_'}|")

    if 'dictionary_item_added' in ddiff.keys():
        for keys in ddiff['dictionary_item_added']:
            global_indent = len(keys)
            key = keys.replace('root[', '').replace('\'', '').replace(']', '').split('[')
            yaml_indent = 0
            print(f" {global_indent * 2 * '_'}")
            diff_type = "Добавился элемент"
            tmp_left_indent = global_indent - len(diff_type) // 2
            tmp_right_indent = global_indent * 2 - (tmp_left_indent + len(diff_type))
            print(f"|{tmp_left_indent * ' '}{diff_type}{tmp_right_indent * ' '}|")
            print(f" {global_indent * 2 * '_'}")
            print(f"|Было{(global_indent - 5) * ' '}|Стало{(global_indent - 5) * ' '}|")
            print(f" {global_indent * 2 * '_'}")
            for elem in key:
                left_space_print = f"|{global_indent * ' '}|"
                right_print = f"{yaml_indent * '    '}{elem}:"
                right_space_print = f"{(global_indent - len(right_print) - 1) * ' '}|"
                print(left_space_print, right_print, right_space_print, sep="")
                yaml_indent += 1
            print(f"|{global_indent * 2 * '_'}|")


def cycle_file_differ(backup_location, dryrun_location, diff_location):
    backup_files = os.listdir(backup_location)
    dryrun_files = os.listdir(dryrun_location)
    for backup_file in backup_files:
        if backup_file in dryrun_files:
            original_stdout = sys.stdout
            with open(f"{dryrun_location}/{backup_file}", "r") as stream:
                try:
                    dry_yaml = yaml.unsafe_load(stream)
                except yaml.YAMLError as exc:
                    print(exc)

            with open(f"{backup_location}/{backup_file}", "w+") as stream:
                try:
                    # temp_backup = stream.read()
                    # temp_backup = temp_backup.replace("application-secure.yml: |-", "application-secure.yml:")
                    # temp_backup = temp_backup.replace("application.yml: |-", "application.yml:")
                    # stream.write(temp_backup)
                    backup_yaml = yaml.unsafe_load(stream)
                except yaml.YAMLError as exc:
                    print(exc)

            clean_yaml_diff = diff(backup_yaml, dry_yaml, ignore=ignored_list)
            with open(f"{diff_location}/{backup_file}.txt", 'w') as out_file:
                sys.stdout = out_file  # Change the standard output to the file we created.
                yaml_diff_printer(list(clean_yaml_diff))
                sys.stdout = original_stdout
        else:
            print(f"Файл {backup_file} отсутсвтует в dryrun")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Paths to directory')
    parser.add_argument('dryrun', type=str, help='Dryrun folder with only one file')
    parser.add_argument('backup', type=str, help='Folder that contains all backup files')
    parser.add_argument('diff', type=str, help='Empty folder for diff files')
    args = parser.parse_args()
    dryrun_file = os.listdir(args.dryrun)[0]
    with open(f"{args.dryrun}/{dryrun_file}", "r") as stream:
        dryrun = stream.read()
        dryrun = dryrun.replace("application-secure.yml: |-", "application-secure.yml:")
        dryrun = dryrun.replace("application.yml: |-", "application.yml:")
        dryrun = re.sub(r"#.+\n", "", dryrun)
        dryrun = dryrun.split('---')

    for elem in dryrun:
        tmp_manifest = yaml.unsafe_load(elem)
        original_stdout = sys.stdout
        with open(f"dryrun/{tmp_manifest['kind'].lower()}-{tmp_manifest['metadata']['name']}.yaml", 'w') as out_file:
            sys.stdout = out_file  # Change the standard output to the file we created.
            print(yaml.dump(tmp_manifest))
            sys.stdout = original_stdout

    cycle_file_differ(args.backup, args.dryrun, args.diff)