class ResultStore:
    def __init__(self):
        self.data = []

    def add_to_database(self, data):
        self.data.append(data)

    def check_status(self, job_id):
        for item in self.data:
            if item["job_id"] == job_id:
                return item
        return {"status": "queued"}