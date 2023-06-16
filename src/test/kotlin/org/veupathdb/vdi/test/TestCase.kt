package org.veupathdb.vdi.test

import com.fasterxml.jackson.annotation.JsonValue

class TestCase(
    val path: String,
    val expectation: Expectation,
    val project: String,
    val type: String
)

class TestSuite(
    val tests: List<TestCase>
)

enum class Expectation(private val value: String) {
    SUCCESS("success"),
    FAILED_IMPORT("failed_import"),
    FAILED_INSTALL("failed_install");

    @JsonValue
    fun getValue(): String {
        return value
    }
}