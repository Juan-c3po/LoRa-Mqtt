""" - """
# pylint: disable=line-too-long

def present(status_bit: int, position: int):
    """returns [true], if the bit located in the given [position] inside [status] is 0"""
    return (status_bit >> position) & 1  # shifts the bit, at the given <position>, to the first position; then apply <logical and> for the first bit

def inside_array(array: bytes, start: int, size: int):
    """returns [true], if reading [size] bits at position [start] for the given [array] will cause overflow"""
    return start + size <= len(array)

def complement_two(val: int, length: int):
    """compute the 2's complement of in
    t value val"""
    if (val & (1 << (length - 1))) != 0:
        val = val - (1 << length)
    return val

def merge_digits(digits: list[int], part: list[int]):
    """merges all digits (numbers between 0 and 9), from index <part[0]> to index <part[1]>, of the <digits> array, into one number. ex: the merge of [1,2,3] results in the number 123 """
    result: int = 0
    for index in range(part[0], part[1] + 1):
        result += digits[index] * pow(10, (part[1] - index))
    return result
