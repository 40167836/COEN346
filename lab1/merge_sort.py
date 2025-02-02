from threading import Thread

input_list = [3304, 8221, 26849, 14038, 1509, 6367, 7856, 21362]

def mergeAlgo(list1, list2):
    sorted_list = []
    i = j = 0

    while i < len(list1) and j < len(list2):
        if list1[i] <= list2[j]:
            sorted_list.append(list1[i])
            i += 1
        else:
            sorted_list.append(list2[j])
            j += 1

    sorted_list.extend(list1[i:])
    sorted_list.extend(list2[j:])
    return sorted_list

class CustomThread(Thread):
    def __init__(self, myList):
        super().__init__()
        self.myList = myList
        self.result = None

    def run(self):
        if all(self.myList[i] <= self.myList[i + 1] for i in range(len(self.myList) - 1)):
            self.result = self.myList
        else:
            mid = len(self.myList) // 2
            thread1 = CustomThread(self.myList[:mid])
            thread2 = CustomThread(self.myList[mid:])
            thread1.start()
            thread2.start()
            thread1.join()
            thread2.join()
            self.result = mergeAlgo(thread1.result, thread2.result)

thread = CustomThread(input_list)
thread.start()
thread.join()

print("Sorted List:", thread.result)