class Result_store:
    def __init__(self):
        self.data = []

    def add_to_database(self, data):
        self.data.append(data)

    def check_status(self, job_id):
        for item in self.data:
            if item["job_id"] == job_id:
                return {"status": item["status"], "response": item.get("response", None)}

        return {"status": "queued",
                "n" : f"{len(self.data)} items in queue."}

result_store = Result_store()