import re
from dataclasses import dataclass
from pathlib import Path

from lxml import etree


@dataclass(slots=True)
class Field:
    name: str
    description: str
    offset: int
    size: int
    access: str

    def gen_declaration(self, ):
        match self.access:
            case "read-write":
                access = "FieldType::ReadWrite"
            case "read-only":
                access = "FieldType::Read"
            case "write-only":
                access = "FieldType::Write"
            case _:
                raise ValueError("Invalid field type.")

        return f"   Field<{access}, address, {self.offset}, {self.size}> {self.name.lower()};"


@dataclass(slots=True)
class Register:
    name: str
    display_name: str
    description: str
    offset: str
    size: int
    reset_value: str
    fields: list[Field]

    def gen_definition(self, parent: str):
        definition = f"template <uint32_t address>\nstruct {self.name}_{parent} {{\n"
        for field in self.fields[::-1]:
            definition += field.gen_declaration() + "\n"
        definition += f"}};\n\n"
        return definition


@dataclass(slots=True)
class Peripheral:
    name: str
    description: str
    group: str
    base_address: str
    offset: str
    size: str
    registers: list[Register]

    def gen_declaration(self):
        declaration = f"{self.name}<{self.base_address}> {self.name.lower()};"
        return declaration

    def gen_definition(self):
        definition = f"template <uint32_t address>\nstruct {self.name} {{\n"
        for register in self.registers:
            definition += f"    {register.name}_{self.name} <address + {register.offset}> {register.name.lower()};\n"
        definition += f"}};\n\n"

        output_file = Path(f"{self.group}/{self.name}.h")
        output_file.parent.mkdir(exist_ok=True, parents=True)
        with open(output_file, "w+", encoding="utf8") as ofile:
            ofile.write(f"#ifndef {self.name}_H\n#define {self.name}_H\n\n#include \"field.h\"\n\n")
            for register in self.registers:
                defi = register.gen_definition(self.name)
                ofile.write(defi)
            ofile.write(definition)
            ofile.write(f"#endif //{self.name}_H")


def gen_peripheral_header(peripherals: list[Peripheral]):
    definition = "struct "

def clean_str(istr: str):
    return re.sub(" +", " ", istr)


with open("STM32WB15_CM4.svd", "r") as ifile:
    data = etree.parse(ifile).getroot()
    peripherals = data.findall("peripherals")[0]
    output = []
    for peripheral in peripherals:
        name = peripheral.findall("name")[0].text
        if len(peripheral.findall("description")) == 0:
            continue
        description = clean_str(peripheral.findall("description")[0].text)
        group = peripheral.findall("groupName")[0].text
        base_address = peripheral.findall("baseAddress")[0].text
        addr_block = peripheral.findall("addressBlock")[0]
        offset = addr_block.findall("offset")[0].text
        size = addr_block.findall("size")[0].text
        register_list = []
        curr_peripheral = Peripheral(name, description, group, base_address, offset, size, register_list)
        output.append(curr_peripheral)

        registers = peripheral.findall("registers")[0].findall("register")
        for register in registers:
            name = register.findall("name")[0].text
            display_name = register.findall("displayName")[0].text
            description = clean_str(register.findall("description")[0].text)
            offset = register.findall("addressOffset")[0].text
            size = register.findall("size")[0].text
            if len(register.findall("access")) > 0:
                reg_access = register.findall("access")[0].text
            else:
                reg_access = None
            reset_value = register.findall("resetValue")[0].text
            field_list = []
            curr_register = Register(name, display_name, description, offset, size, reset_value, field_list)
            curr_peripheral.registers.append(curr_register)

            fields = register.findall("fields")[0].findall("field")
            for field in fields:
                name = field.findall("name")[0].text
                description = field.findall("description")[0].text
                offset = field.findall("bitOffset")[0].text
                size = field.findall("bitWidth")[0].text
                if reg_access is None:
                    access = field.findall("access")[0].text
                else:
                    access = reg_access
                curr_register.fields.append(Field(name, clean_str(description), int(offset), int(size), access))
        curr_peripheral.gen_definition()