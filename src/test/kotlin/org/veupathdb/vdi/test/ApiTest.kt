package org.veupathdb.vdi.test

import com.fasterxml.jackson.databind.ObjectMapper
import io.restassured.RestAssured
import io.restassured.RestAssured.given
import io.restassured.http.ContentType
import org.apache.logging.log4j.kotlin.logger
import org.awaitility.Awaitility.await
import org.awaitility.core.ConditionTimeoutException
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.MethodSource
import java.net.URL
import java.nio.file.FileVisitOption
import java.nio.file.Files
import java.nio.file.Path
import java.time.Duration
import java.util.stream.Stream
import kotlin.io.path.isDirectory
import kotlin.io.path.name


@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class ApiTest {
    private val AuthToken: String = System.getProperty("AUTH_TOKEN")
    private val AuthTokenKey: String = "Auth-Key"
    private val ObjectMapper = ObjectMapper()

    // Files in the testdata resource directory must follow structure testdata/{dataset-type}/{upload-file}
    private val TestFilesDir = "testdata"

    // Keep track of all datasets created to clean them after all tests are done.
    private val DatasetsToClean = mutableListOf<String>()

    @BeforeAll
    internal fun setup() {
        RestAssured.baseURI = System.getProperty("BASE_URL")
    }

    @AfterAll
    internal fun teardown() {
        DatasetsToClean.forEach {
            logger().info("Cleaning dataset $it")
            given()
                .header("Auth-Key", System.getProperty("AUTH_TOKEN"))
                .`when`()
                .delete("vdi-datasets/$it")
                .then()
                .statusCode(204)
        }
    }

    @ParameterizedTest
    @MethodSource("fileProvider")
    fun parameterizedTest(input: TestCase) {
        val meta: Map<String, Any> = mapOf(
            Pair(
                "datasetType",
                mapOf(
                    Pair("name", input.type),
                    Pair("version", "1.0")
                )
            ),
            Pair("name", input.path.fileName),
            Pair("summary", "Integration test case for file ${input.path.fileName}"),
            Pair("projects", listOf(input.project)),
            Pair("dependencies", emptyList<String>())
        )
        val datasetID = given() // Setup request
            .contentType(ContentType.MULTIPART)
            .header(AuthTokenKey, AuthToken)
            .multiPart("file", input.path.toFile())
            .multiPart("meta", ObjectMapper.writeValueAsString(meta))
            // Execute request
            .`when`()
            .post("vdi-datasets")
            // Validate request and extract ID
            .then()
            .statusCode(input.status)
            .extract()
            .path<String>("datasetID")
        DatasetsToClean.add(datasetID)

        awaitImportStatus(datasetID, "complete")
        awaitInstallStatus(datasetID, "complete")
        logger().info("Completed install of dataset $datasetID")
    }

    private fun fileProvider(): Stream<TestCase> {
        val loader = Thread.currentThread().contextClassLoader
        val url: URL = loader.getResource(TestFilesDir)!!
        val path: String = url.path
        return Files.walk(Path.of(path), FileVisitOption.FOLLOW_LINKS)
            .filter { file -> !file.isDirectory() }
            .map { file -> TestCase(file, 200, file.parent.name, "PlasmoDB") } // TODO Determine what status and project we should use for the test.
    }

    class TestCase(
        val path: Path,
        val status: Int,
        val project: String,
        val type: String
    )

    private fun awaitInstallStatus(datasetID: String, status: String) {
        try {
            await()
                .atMost(Duration.ofSeconds(30L))
                .until {
                    getInstallStatus(datasetID) == status
                }
        } catch (e: ConditionTimeoutException) {
            throw AssertionError(
                "Test failed while waiting for inst all status of $datasetID to become \"complete\". " +
                        "Current status: ${getInstallStatus(datasetID)})", e
            )
        }
    }

    private fun awaitImportStatus(datasetID: String, status: String) {
        try {
            await()
                .pollInterval(Duration.ofSeconds(1L))
                .atMost(Duration.ofSeconds(30L))
                .until {
                    getImportStatus(datasetID) == status
                }
        } catch (e: ConditionTimeoutException) {
            throw AssertionError(
                "Test failed while waiting for import status of $datasetID to become \"complete\". " +
                        "Current status: ${getImportStatus(datasetID)})", e
            )
        }
    }

    private fun getImportStatus(datasetID: String): String {
        return given()
            .header(AuthTokenKey, AuthToken)
            .get("vdi-datasets/$datasetID")
            .then()
            .statusCode(200)
            .extract()
            .path("status.import")
    }

    private fun getInstallStatus(datasetID: String): String? {
        val node: Map<String, String> = given()
            .header(AuthTokenKey, AuthToken)
            .get("vdi-datasets/$datasetID")
            .then()
            .statusCode(200)
            .extract()
            .path("status.install[0]")
        return node["dataStatus"]
    }
}