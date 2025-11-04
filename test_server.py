#!/usr/bin/env python3

import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from server import (
    mcp,
    analyze_file_changes,
    get_pr_templates,
    suggest_template,
    # create_default_template,
    TEMPLATES_DIR
)


class TestAnalyzeFileChanges:
    @pytest.mark.asyncio
    async def test_analyze_with_diff(self):
        mock_result = MagicMock()
        mock_result.stdout = "M\tfile1.py\nA\tfile2.py\n"
        mock_result.stderr = ""
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = mock_result
            
            result = await analyze_file_changes("main", include_diff=True)
            
            assert isinstance(result, str)
            data = json.loads(result)
            assert data["base_branch"] == "main"
            assert "files_changed" in data
            assert "statistics" in data
            assert "commits" in data
            assert "diff" in data
    
    @pytest.mark.asyncio
    async def test_analyze_without_diff(self):
        mock_result = MagicMock()
        mock_result.stdout = "M\tfile1.py\n"
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = mock_result
            
            result = await analyze_file_changes("main", include_diff=False)
            
            data = json.loads(result)
            assert "Diff not included" in data["diff"]
    
    @pytest.mark.asyncio
    async def test_analyze_git_error(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Git not found")
            
            result = await analyze_file_changes("main", True)
            
            assert "error" in result


class TestPRTemplates:
    @pytest.mark.asyncio
    async def test_get_templates(self, tmp_path, monkeypatch):
        # Set up test templates in the temporary directory
        templates_dir = Path(__file__).parent / "templates"
        monkeypatch.setattr('server.TEMPLATES_DIR', templates_dir)
        
        # Call the function under test
        result = await get_pr_templates()
        
        # Verify the results
        templates = json.loads(result)
        assert len(templates) > 0
        assert any(t["type"] == "Bug Fix" for t in templates)
        assert any(t["type"] == "Feature" for t in templates)
        assert all("content" in t for t in templates)
    
    # def test_create_default_template(self, tmp_path):
    #     template_path = tmp_path / "test.md"
        
    #     create_default_template(template_path, "Bug Fix")
        
    #     assert template_path.exists()
    #     content = template_path.read_text()
    #     assert "## Bug Fix" in content
    #     assert "Description" in content
    #     assert "Root Cause" in content


class TestSuggestTemplate:
    @pytest.mark.asyncio
    async def test_suggest_bug_fix(self, tmp_path, monkeypatch):
        tmp_path = Path(__file__).parent / "templates"
        monkeypatch.setattr('server.TEMPLATES_DIR', tmp_path)
        
        # Create templates first
        await get_pr_templates()
        
        result = await suggest_template(
            "Fixed null pointer exception in user service",
            "bug"
        )
        
        suggestion = json.loads(result)
        assert suggestion["recommended_template"]["filename"] == "bug.md"
        assert "Bug Fix" in suggestion["recommended_template"]["type"]
        assert "reasoning" in suggestion
    
    @pytest.mark.asyncio
    async def test_suggest_feature(self, tmp_path, monkeypatch):
        tmp_path = Path(__file__).parent / "templates"
        monkeypatch.setattr('server.TEMPLATES_DIR', tmp_path)
        
        await get_pr_templates()
        
        result = await suggest_template(
            "Added new authentication method for API",
            "feature"
        )
        
        suggestion = json.loads(result)
        assert suggestion["recommended_template"]["filename"] == "feature.md"
    
    @pytest.mark.asyncio
    async def test_suggest_with_type_variations(self, tmp_path, monkeypatch):
        tmp_path = Path(__file__).parent / "templates"
        monkeypatch.setattr('server.TEMPLATES_DIR', tmp_path)
        
        await get_pr_templates()
        
        # Test variations
        for change_type, expected_file in [
            ("fix", "bug.md"),
            ("enhancement", "feature.md"),
            ("documentation", "docs.md"),
            ("cleanup", "refactor.md"),
            ("testing", "test.md"),
            ("optimization", "performance.md")
        ]:
            result = await suggest_template(f"Some {change_type} work", change_type)
            suggestion = json.loads(result)
            assert suggestion["recommended_template"]["filename"] == expected_file


class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path, monkeypatch):
        tmp_path = Path(__file__).parent / "templates"
        monkeypatch.setattr('server.TEMPLATES_DIR', tmp_path)
        
        # Mock git commands
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout="M\tsrc/main.py\nM\ttests/test_main.py\n",
                stderr=""
            )
            
            analysis_result = await analyze_file_changes("main", True)
            templates_result = await get_pr_templates()
            suggestion_result = await suggest_template(
                "Updated main functionality and added tests",
                "feature"
            )
            assert all(isinstance(r, str) for r in [analysis_result, templates_result, suggestion_result])
            
            suggestion = json.loads(suggestion_result)
            assert "recommended_template" in suggestion
            assert "template_content" in suggestion
            assert suggestion["recommended_template"]["type"] == "Feature"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])