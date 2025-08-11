"""Module for processing OpenAPI files."""

import json
from pathlib import Path
from typing import Any

import httpx
import yaml
from schemax import collect_schema_data, SchemaData


class OpenAPIProcessor:
    """Class for processing OpenAPI files and extracting schema data."""

    def process_openapi_file(self, openapi_file_path: str | Path) -> list[SchemaData]:
        """Public method for processing OpenAPI file.

        Args:
            openapi_file_path: Path to OpenAPI file (JSON or YAML)

        Returns:
            Collected schema data

        Raises:
            FileNotFoundError: If file is not found
            ValueError: If file has unsupported format
            Exception: On parsing or processing errors
        """
        file_path = Path(openapi_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"OpenAPI file not found: {file_path}")

        openapi_schema = self._load_openapi_file(file_path)
        return self._process_schema(openapi_schema)

    def process_openapi_url(self, openapi_url: str, timeout: float = 30.0) -> list[SchemaData]:
        """Public method for processing OpenAPI file by URL.

        Args:
            openapi_url: URL to download OpenAPI file
            timeout: HTTP request timeout in seconds (default 30)

        Returns:
            Collected schema data

        Raises:
            httpx.HTTPError: On HTTP request errors
            ValueError: If file has unsupported format
            Exception: On parsing or processing errors
        """
        openapi_schema = self._load_openapi_url(openapi_url, timeout)
        return self._process_schema(openapi_schema)

    @staticmethod
    def _process_schema(openapi_schema: dict[str, Any]) -> list[SchemaData]:
        """Processes OpenAPI schema using collect_schema_data.

        Args:
            openapi_schema: Parsed OpenAPI schema

        Returns:
            Collected schema data
        """
        collected_data = collect_schema_data(openapi_schema)

        return collected_data

    @staticmethod
    def _load_openapi_url(url: str, timeout: float) -> dict[str, Any]:
        """
        Loads OpenAPI file by URL.

        Args:
            url: URL to download file
            timeout: Request timeout

        Returns:
            Parsed OpenAPI schema

        Raises:
            httpx.HTTPError: On HTTP request errors
            ValueError: If file format is not supported
        """
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url)
                response.raise_for_status()

                content = response.text
                content_type = response.headers.get('content-type', '').lower()

                # Determine format by Content-Type or try both formats
                if 'application/json' in content_type or 'json' in content_type:
                    return json.loads(content)
                elif 'application/yaml' in content_type or 'text/yaml' in content_type or 'yaml' in content_type:
                    return yaml.safe_load(content)
                else:
                    # Try to determine format by content
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        try:
                            return yaml.safe_load(content)
                        except yaml.YAMLError:
                            raise ValueError(
                                f"Unsupported file format from URL: {url}. "
                                "Only JSON and YAML formats are supported."
                            )

        except httpx.HTTPError as e:
            raise httpx.HTTPError(f"Error loading OpenAPI file from URL {url}: {e}")
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise Exception(f"Error parsing OpenAPI file: {e}")
        except Exception as e:
            raise Exception(f"Error processing URL: {e}")

    @staticmethod
    def _load_openapi_file(file_path: Path) -> dict[str, Any]:
        """
        Loads OpenAPI file depending on its format.

        Args:
            file_path: Path to file

        Returns:
            Parsed OpenAPI schema

        Raises:
            ValueError: If file format is not supported
        """
        file_extension = file_path.suffix.lower()

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                if file_extension in ['.json']:
                    return json.load(file)
                elif file_extension in ['.yaml', '.yml']:
                    return yaml.safe_load(file)
                else:
                    # Try to determine format by content
                    content = file.read()
                    file.seek(0)

                    # Try JSON first
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        # If not JSON, try YAML
                        try:
                            return yaml.safe_load(content)
                        except yaml.YAMLError:
                            raise ValueError(
                                f"Unsupported file format: {file_extension}. "
                                "Only JSON and YAML formats are supported."
                            )
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise Exception(f"Error parsing OpenAPI file: {e}")
        except Exception as e:
            raise Exception(f"Error reading file: {e}")


if __name__ == '__main__':
    processor = OpenAPIProcessor()
    print(processor.process_openapi_file(Path("schema.json")))
