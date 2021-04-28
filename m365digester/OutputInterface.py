class OutputInterface:

    def set_input(self, rule_list: dict) -> bool:
        pass

    def set_target_file_path(self, target_file_path: str) -> bool:
        pass

    def get_file_extension(self) -> str:
        pass

    def run(self) -> bool:
        pass
