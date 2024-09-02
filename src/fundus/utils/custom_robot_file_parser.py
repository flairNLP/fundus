import urllib.parse
from typing import Iterator, Dict, List

from robots import RobotFileParser
import re

from robots.parser import RE_AGENT, Token, TokenType, RE_RULE_ALLOW, RE_RULE_DISSALLOW, RE_SITEMAP, State, Rule, Errors

# Crawl Delay
RE_CRAWL_DELAY = re.compile(
    r"^\s*crawl-delay\s*:\s*(?P<DELAY>[0-9]+)\s*$",
    re.IGNORECASE | re.VERBOSE,
)


def gen_tokens(gen_func, source):
    """Token generator.

    Emit tokens when parsing the content of a robots.txt
    """
    linenum = 0
    for line in gen_func(source):
        linenum += 1
        # pylint: disable=superfluous-parens
        if not (line := line.strip()):
            continue  # Skip empty lines
        if line.startswith("#"):
            continue  # Skip line comment
        if m := RE_AGENT.match(line):
            agent = m.group("AGENT")
            yield Token(TokenType.AGENT, agent, linenum)
        elif m := RE_RULE_ALLOW.match(line):
            path = m.group("PATH")
            yield Token(TokenType.ALLOW, path, linenum)
        elif m := RE_RULE_DISSALLOW.match(line):
            path = m.group("PATH")
            yield Token(TokenType.DISALLOW, path, linenum)
        elif m := RE_SITEMAP.match(line):
            sitemap = m.group("SITEMAP")
            yield Token(TokenType.SITEMAP, sitemap, linenum)
        elif m := RE_CRAWL_DELAY.match(line):
            delay = m.group("DELAY")
            yield Token(TokenType.CRAWL_DELAY, delay, linenum)
        else:
            yield Token(TokenType.UNEXPECTED, line, linenum)


class CustomRobotFileParser(RobotFileParser):
    _crawl_delay: Dict[str, int] = {}

    def update_crawl_delay(self, agents, crawl_delay: int):
        for agent in agents:
            self._crawl_delay[agent] = crawl_delay

    def read(self):
        """Populate the tokens if a URL is assigned to the url attribute --- adapted from robots library"""
        if self.url:
            self.parse_tokens(gen_tokens(self.gen_uri, self.url))
        else:
            self._errors.append(
                (
                    self.url,
                    "RobotFileParser.read requires RobotFileParser.url to be set",
                )
            )

    def parse_tokens(self, tokens: Iterator) -> None:
        """Main function of the parser. --- adapted from robots library

        Parse a robots.txt file and generate a data structure that can then be used by the
        Robots object to answer question (can_fetch?) given a URL and a robots ID.
        """

        state = State.BEGIN
        current_agents: List[str] = []
        current_rules: List[Rule] = []
        current_crawl_delay = 0

        for token in tokens:
            if token.type == TokenType.AGENT:
                if state == State.RULE:
                    self.update_rules(current_agents, current_rules)
                    self.update_crawl_delay(current_agents, current_crawl_delay)
                    current_agents = []
                    current_rules = []
                    current_crawl_delay = 0
                state = State.AGENT
                current_agents.append(token.value.lower())
            elif token.type in (TokenType.ALLOW, TokenType.DISALLOW):
                if state == State.BEGIN:
                    self._warnings.append(
                        (
                            f"line {token.linenum}",
                            Errors.WARNING_RULE_WITHOUT_AGENT.value,
                        )
                    )
                    continue  # A rule without an agent is ignored
                state = State.RULE
                if path := token.value:
                    current_rules.append(Rule(urllib.parse.unquote(path), token.type == TokenType.ALLOW))
                else:
                    if token.type == TokenType.ALLOW:
                        self._warnings.append((f"line {token.linenum}", Errors.WARNING_EMPTY_ALLOW_RULE))
            elif token.type == TokenType.CRAWL_DELAY:
                if state == State.BEGIN:
                    self._warnings.append(
                        (
                            f"line {token.linenum}",
                            "Warning: Delay without an agent is ignored",
                        )
                    )
                    continue  # A delay without an agent is ignored
                try:
                    if current_crawl_delay := int(token.value):
                        state = State.RULE
                except ValueError:
                    self._warnings.append(
                        (
                            f"line {token.linenum}",
                            "Warning: Delay is not an integer",
                        )
                    )
                    current_crawl_delay = 0
            elif token.type == TokenType.SITEMAP:
                self._sitemaps.append(token.value)
            else:
                # Unprocessed or unexpected token
                self._warnings.append(
                    (
                        f"line {token.linenum}",
                        f"{Errors.WARNING_UNEXPECTED_OR_IGNORED}: {token.value}",
                    )
                )

        self.update_rules(current_agents, current_rules)

    def crawl_delay(self, user_agent: str) -> int:
        return self._crawl_delay.get(user_agent.lower()) or 0
