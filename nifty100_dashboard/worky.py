class CountUp:
    def __init__(self, max_val):
        self.max_val = max_val
        self.current = 0
    def __iter__(self):
        return self
    def __next__(self):
        if self.current >= self.max_val:
            raise StopIteration
        self.current += 1
        return self.current

for num in CountUp(5):
    print(num)          # 1 2 3 4 5






import functools

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper