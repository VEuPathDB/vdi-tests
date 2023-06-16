import org.gradle.api.tasks.testing.logging.TestLogEvent

plugins {
  kotlin("jvm") version "1.8.21"
}

dependencies {
  implementation(kotlin("stdlib-jdk8"))

  testImplementation("com.fasterxml.jackson.core:jackson-core:2.15.1")
  testImplementation("com.fasterxml.jackson.core:jackson-databind:2.15.1")
  testImplementation("com.fasterxml.jackson.module:jackson-module-kotlin:2.15.1")
  testImplementation("com.fasterxml.jackson.dataformat:jackson-dataformat-yaml:2.15.1")

  testImplementation("org.awaitility:awaitility:4.2.0")
  testImplementation("org.junit.jupiter:junit-jupiter:5.9.2")
  testImplementation("io.rest-assured:rest-assured:5.3.0")
  testImplementation("io.rest-assured:json-path:5.3.0")
  testImplementation("org.slf4j:slf4j-api:2.0.5")
  testImplementation("org.apache.logging.log4j:log4j-api-kotlin:1.2.0")
  testImplementation("org.apache.logging.log4j:log4j-core:2.20.0")
}


tasks.register<Test>("api-test") {
  systemProperty("AUTH_TOKEN", System.getenv("AUTH_TOKEN"))
  systemProperty("BASE_URL", System.getenv("VDI_BASE_URL"))

  useJUnitPlatform()
  testLogging {
    events = setOf(TestLogEvent.STANDARD_OUT, TestLogEvent.STARTED, TestLogEvent.PASSED, TestLogEvent.SKIPPED, TestLogEvent.FAILED)
    showStackTraces = true
    showStandardStreams = true
  }
}

repositories {
  mavenCentral()
}
