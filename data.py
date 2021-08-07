import json, requests, os, sys

with open(os.path.join("data", "locales.json"), "r") as f:
    locales = json.load(f)

SET_AMOUNT = 4

class DataDragon():
    def __init__(self):
        self.globals = {}
        self.sets = {}
        while True:
            try:
                print("Loading data...")
                self.load_data()
                break
            except Exception as err:
                if (type(err) == FileNotFoundError):
                    print("Seem you haven't had any local data yet.")
                    self.update_data()
                else: raise err
    def update_data(self):
        print("Updating data from Riot's Data Dragon...")
        for l in locales:
            l_path = "data/" + l
            if (not os.path.isdir(l_path)): os.mkdir(l_path)
            r = requests.get(f"https://dd.b.pvp.net/latest/core/{l}/data/globals-{l}.json").content.decode('utf-8')
            # with open(os.path.join(l_path, "debug.json"), "w") as f: json.dump(r, f)
            r = "\n".join(r.splitlines())
            with open(os.path.join(l_path, "globals.json"), "w") as f: f.write(r)
            for i in range(1, SET_AMOUNT + 1):
                r = requests.get(f"https://dd.b.pvp.net/latest/set{i}/{l}/data/set{i}-{l}.json").content.decode('utf-8')
                r = "\n".join(r.splitlines())
                with open(os.path.join(l_path, f"set{i}.json"), "w") as f: f.write(r)
    def load_data(self):
        for l in locales:
            l_path = "data/" + l
            with open(os.path.join(l_path, "globals.json"), "r", encoding="utf-8") as f: self.globals[l] = json.load(f)
            sets_data = []
            for i in range(1, SET_AMOUNT + 1):
                with open(os.path.join(l_path, f"set{i}.json"), "r", encoding="utf-8") as f: sets_data.append(json.load(f))
            self.sets[l] = sets_data


if (__name__ == "__main__"):
    dd = DataDragon()
