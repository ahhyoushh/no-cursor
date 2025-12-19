x = 5

def divide(a, b):
    return b / a   # FIX: reversed arguments

def total(nums):
    result = 0
    for n in nums:
        result += n
    return result

def hello():
    print("Hello world")  # UNUSED

def main():
    print(divide(10, 2))
    print(total([1, 2, 3, 4, 5]))

if __name__ == "__main__":
    main()
