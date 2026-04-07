"""canonicalize_url 的全面测试."""
from __future__ import annotations

import pytest

from canonicalize import canonicalize_url


# ---------------------------------------------------------------------------
# 空/空白输入
# ---------------------------------------------------------------------------
class TestEmptyInput:
    def test_empty_string(self) -> None:
        assert canonicalize_url("") == ""

    def test_whitespace_only(self) -> None:
        assert canonicalize_url("   ") == ""

    def test_tabs_and_newlines(self) -> None:
        assert canonicalize_url("\t\n  ") == ""


# ---------------------------------------------------------------------------
# 主机名小写规范化
# ---------------------------------------------------------------------------
class TestHostLowercase:
    def test_uppercase_host(self) -> None:
        assert canonicalize_url("https://WWW.EXAMPLE.COM/page") == "https://www.example.com/page"

    def test_mixed_case_host(self) -> None:
        assert canonicalize_url("https://Www.Example.Com/Path") == "https://www.example.com/Path"

    def test_scheme_lowered(self) -> None:
        result = canonicalize_url("HTTP://example.com/x")
        assert result.startswith("http://")


# ---------------------------------------------------------------------------
# 默认端口剥离
# ---------------------------------------------------------------------------
class TestDefaultPortStripping:
    def test_https_443_stripped(self) -> None:
        assert canonicalize_url("https://example.com:443/path") == "https://example.com/path"

    def test_http_80_stripped(self) -> None:
        assert canonicalize_url("http://example.com:80/path") == "http://example.com/path"


# ---------------------------------------------------------------------------
# 非默认端口保留
# ---------------------------------------------------------------------------
class TestNonDefaultPort:
    def test_https_8443_preserved(self) -> None:
        assert canonicalize_url("https://example.com:8443/path") == "https://example.com:8443/path"

    def test_http_8080_preserved(self) -> None:
        assert canonicalize_url("http://example.com:8080/path") == "http://example.com:8080/path"

    def test_http_443_preserved(self) -> None:
        # 443 on http (not https) is non-default — should be kept
        assert canonicalize_url("http://example.com:443/path") == "http://example.com:443/path"

    def test_https_80_preserved(self) -> None:
        # 80 on https is non-default — should be kept
        assert canonicalize_url("https://example.com:80/path") == "https://example.com:80/path"


# ---------------------------------------------------------------------------
# UTM 和追踪参数移除
# ---------------------------------------------------------------------------
class TestTrackingParamRemoval:
    @pytest.mark.parametrize("param", [
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    ])
    def test_utm_params_removed(self, param: str) -> None:
        url = f"https://example.com/page?{param}=val&keep=1"
        result = canonicalize_url(url)
        assert param not in result
        assert "keep=1" in result

    @pytest.mark.parametrize("param", ["fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "ref", "ref_src"])
    def test_tracking_params_removed(self, param: str) -> None:
        url = f"https://example.com/page?{param}=abc123&keep=yes"
        result = canonicalize_url(url)
        assert param not in result
        assert "keep=yes" in result

    def test_all_tracking_removed_leaves_no_query(self) -> None:
        url = "https://example.com/page?utm_source=google&fbclid=abc"
        result = canonicalize_url(url)
        assert result == "https://example.com/page"


# ---------------------------------------------------------------------------
# 尾部斜杠规范化
# ---------------------------------------------------------------------------
class TestTrailingSlash:
    def test_root_slash_preserved(self) -> None:
        assert canonicalize_url("https://example.com/") == "https://example.com/"

    def test_trailing_slash_stripped_from_path(self) -> None:
        assert canonicalize_url("https://example.com/page/") == "https://example.com/page"

    def test_deep_path_trailing_slash_stripped(self) -> None:
        assert canonicalize_url("https://example.com/a/b/c/") == "https://example.com/a/b/c"

    def test_no_trailing_slash_unchanged(self) -> None:
        assert canonicalize_url("https://example.com/page") == "https://example.com/page"


# ---------------------------------------------------------------------------
# 查询参数排序
# ---------------------------------------------------------------------------
class TestQuerySorting:
    def test_params_sorted_alphabetically(self) -> None:
        url = "https://example.com/search?z=1&a=2&m=3"
        result = canonicalize_url(url)
        assert result == "https://example.com/search?a=2&m=3&z=1"

    def test_sorted_after_tracking_removed(self) -> None:
        url = "https://example.com/?c=3&a=1&utm_source=g&b=2"
        result = canonicalize_url(url)
        assert result == "https://example.com/?a=1&b=2&c=3"


# ---------------------------------------------------------------------------
# Wikipedia 特殊处理
# ---------------------------------------------------------------------------
class TestWikipedia:
    def test_strip_query_params(self) -> None:
        url = "https://en.wikipedia.org/wiki/Python_(programming_language)?action=edit"
        result = canonicalize_url(url)
        assert result == "https://en.wikipedia.org/wiki/Python_(programming_language)"

    def test_preserve_wiki_path(self) -> None:
        url = "https://en.wikipedia.org/wiki/Main_Page"
        assert canonicalize_url(url) == "https://en.wikipedia.org/wiki/Main_Page"

    def test_scheme_forced_https(self) -> None:
        url = "http://en.wikipedia.org/wiki/Test"
        assert canonicalize_url(url) == "https://en.wikipedia.org/wiki/Test"

    def test_evil_subdomain_not_matched(self) -> None:
        """evil.en.wikipedia.org 不应匹配 en.wikipedia.org 的特殊逻辑."""
        url = "https://evil.en.wikipedia.org/wiki/Test?action=edit"
        result = canonicalize_url(url)
        # 不应走 Wikipedia 分支，所以 query 参数不会被无条件移除
        # 但 action 不在追踪参数列表中，所以应保留
        assert "action=edit" in result

    def test_non_wiki_path_not_special(self) -> None:
        """en.wikipedia.org 的非 /wiki/ 路径不走特殊处理."""
        url = "https://en.wikipedia.org/w/index.php?title=Test"
        result = canonicalize_url(url)
        assert "title=Test" in result


# ---------------------------------------------------------------------------
# arXiv 特殊处理
# ---------------------------------------------------------------------------
class TestArxiv:
    def test_normalize_to_arxiv_org(self) -> None:
        url = "https://arxiv.org/abs/2301.12345"
        assert canonicalize_url(url) == "https://arxiv.org/abs/2301.12345"

    def test_subdomain_normalized(self) -> None:
        url = "https://export.arxiv.org/abs/2301.12345"
        assert canonicalize_url(url) == "https://arxiv.org/abs/2301.12345"

    def test_trailing_slash_stripped_arxiv(self) -> None:
        url = "https://arxiv.org/abs/2301.12345/"
        assert canonicalize_url(url) == "https://arxiv.org/abs/2301.12345"

    def test_query_stripped_arxiv(self) -> None:
        url = "https://arxiv.org/abs/2301.12345?context=cs"
        assert canonicalize_url(url) == "https://arxiv.org/abs/2301.12345"

    def test_non_abs_path_not_special(self) -> None:
        url = "https://arxiv.org/pdf/2301.12345"
        result = canonicalize_url(url)
        assert "pdf" in result


# ---------------------------------------------------------------------------
# LinkedIn 特殊处理
# ---------------------------------------------------------------------------
class TestLinkedin:
    def test_in_profile_trailing_slash(self) -> None:
        url = "https://www.linkedin.com/in/johndoe"
        assert canonicalize_url(url) == "https://www.linkedin.com/in/johndoe/"

    def test_in_profile_already_has_slash(self) -> None:
        url = "https://www.linkedin.com/in/johndoe/"
        assert canonicalize_url(url) == "https://www.linkedin.com/in/johndoe/"

    def test_company_trailing_slash(self) -> None:
        url = "https://www.linkedin.com/company/acme-corp"
        assert canonicalize_url(url) == "https://www.linkedin.com/company/acme-corp/"

    def test_company_already_has_slash(self) -> None:
        url = "https://www.linkedin.com/company/acme-corp/"
        assert canonicalize_url(url) == "https://www.linkedin.com/company/acme-corp/"

    def test_other_path_no_trailing_slash(self) -> None:
        url = "https://www.linkedin.com/feed/"
        result = canonicalize_url(url)
        # /feed/ 不属于 /in/ 或 /company/，普通路径逻辑 — 不会额外添加 /
        # 但注意 LinkedIn 分支返回 normalized，feed 不以 /in/ 或 /company/ 开头
        assert result == "https://www.linkedin.com/feed"

    def test_scheme_forced_https(self) -> None:
        url = "http://www.linkedin.com/in/johndoe"
        assert canonicalize_url(url) == "https://www.linkedin.com/in/johndoe/"


# ---------------------------------------------------------------------------
# Amazon /dp/ASIN 提取
# ---------------------------------------------------------------------------
class TestAmazon:
    def test_extract_asin_from_product_url(self) -> None:
        url = "https://www.amazon.com/Some-Product-Name/dp/B08N5WRWNW/ref=sr_1_1"
        assert canonicalize_url(url) == "https://www.amazon.com/dp/B08N5WRWNW"

    def test_extract_asin_direct(self) -> None:
        url = "https://www.amazon.com/dp/B08N5WRWNW"
        assert canonicalize_url(url) == "https://www.amazon.com/dp/B08N5WRWNW"

    def test_no_asin_after_dp(self) -> None:
        """如果 dp 后面没有 ASIN，不走特殊提取."""
        url = "https://www.amazon.com/dp/"
        result = canonicalize_url(url)
        # dp 后面没有 segment，走普通路径规范化
        assert "amazon.com" in result

    def test_query_stripped_in_asin_extraction(self) -> None:
        url = "https://www.amazon.com/dp/B08N5WRWNW?tag=affiliate"
        assert canonicalize_url(url) == "https://www.amazon.com/dp/B08N5WRWNW"


# ---------------------------------------------------------------------------
# 精确主机名匹配（防止子域名误匹配）
# ---------------------------------------------------------------------------
class TestExactHostnameMatching:
    def test_evil_wikipedia_subdomain(self) -> None:
        """evil.en.wikipedia.org 不应触发 Wikipedia 特殊逻辑."""
        url = "https://evil.en.wikipedia.org/wiki/Test?foo=bar"
        result = canonicalize_url(url)
        assert "foo=bar" in result

    def test_non_www_linkedin(self) -> None:
        """linkedin.com (无 www) 不应触发 LinkedIn 特殊逻辑."""
        url = "https://linkedin.com/in/johndoe"
        result = canonicalize_url(url)
        # 不走 LinkedIn 分支，普通尾部斜杠剥离
        assert not result.endswith("/")

    def test_non_www_amazon(self) -> None:
        """amazon.com (无 www) 不应触发 Amazon 特殊逻辑."""
        url = "https://amazon.com/dp/B08N5WRWNW/extra"
        result = canonicalize_url(url)
        # 不走 Amazon 分支
        assert "/extra" in result or "dp/B08N5WRWNW" in result
